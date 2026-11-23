import asyncio
import logging
import math
from collections import defaultdict
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import Depends, HTTPException

from app.modules.annonces.client import ScrapeUnblockerClientDep
from app.modules.annonces.detail_repository import DetailRepositoryDep
from app.modules.annonces.dto import AnnonceFiltersDto, MapQueryDto, ScrapeRequestDto
from app.modules.annonces.geocoding import GeocodingServiceDep, address_key
from app.modules.annonces.models import (
    Listing,
    ParsedPage,
    PropertyType,
    SearchCriteria,
    SortOrder,
    TransactionType,
    Zone,
    ZoneLevel,
)
from app.modules.annonces.normalizer import normalize
from app.modules.annonces.repository import AnnonceRepositoryDep, commune_citycodes, department_of
from app.modules.annonces.sources import SOURCES, InvalidCriteria, ParseError, ScraperSource

logger = logging.getLogger(__name__)

# Scraping automatique d'un département affiché sur la carte (chaque page coûte un crédit ScrapeUnblocker).
AUTO_SCRAPE_PAGES = 3
# Délai avant de réinterroger un site pour une zone restée sans annonce, ou après une erreur.
RETRY_EMPTY_MINUTES = 24 * 60
RETRY_ERROR_MINUTES = 10

# Scraping d'un département pour la carte, par (site, département, transaction) : lancé en tâche de fond,
# un seul à la fois ; son résultat est gardé jusqu'à la prochaine demande de la carte, qui l'affiche.
_zone_locks: defaultdict[tuple, asyncio.Lock] = defaultdict(asyncio.Lock)
_running: dict[tuple, asyncio.Task] = {}
_finished: dict[tuple, dict[str, Any]] = {}
# De même pour la page d'une annonce (double clic, plusieurs onglets…).
_detail_locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


class AnnoncesService:
    """Orchestration d'un scraping : URL → page HTML → annonces → normalisation → géocodage → base."""

    def __init__(
        self,
        client: ScrapeUnblockerClientDep,
        geocoding: GeocodingServiceDep,
        repository: AnnonceRepositoryDep,
        details: DetailRepositoryDep,
    ) -> None:
        self.client = client
        self.geocoding = geocoding
        self.repository = repository
        self.details = details

    # ------------------------------------------------------------------ #
    # Fiche complète d'une annonce
    # ------------------------------------------------------------------ #

    async def get_details(self, annonce_id: int, refresh: bool = False) -> dict[str, Any]:
        """Fiche complète d'une annonce : depuis MongoDB si elle y est déjà, sinon lue sur la page de l'annonce
        (un crédit ScrapeUnblocker) puis enregistrée. `refresh` force une nouvelle lecture de la page."""
        annonce = await self.repository.get(annonce_id)
        if annonce is None:
            raise HTTPException(404, f"Annonce {annonce_id} introuvable")
        source = _source(annonce["source"])
        meta = {"annonce_id": annonce_id, "source_label": source.label}

        async with _detail_locks[annonce_id]:
            if not refresh and (cached := await self.details.find(annonce["source"], annonce["source_id"])):
                return {**cached, **meta, "cached": True}

            html = await self.client.get_page_source(annonce["url"])
            try:
                detail = source.parse_detail(html)
            except NotImplementedError as exc:
                raise HTTPException(501, str(exc)) from exc
            except ParseError as exc:
                raise HTTPException(502, f"{exc} : {annonce['url']}") from exc
            saved = await self.details.save(
                annonce["source"], annonce["source_id"], annonce["url"], detail, datetime.now(timezone.utc)
            )
            if detail.images:  # annonce enregistrée avant le stockage des photos : on comble le manque
                await self.repository.set_image_if_missing(annonce_id, detail.images[0].url)
        logger.info("%s %s : fiche enregistrée (%d images)", source.name, annonce["source_id"], len(detail.images))
        return {**saved, **meta, "cached": False}

    # ------------------------------------------------------------------ #
    # Lecture
    # ------------------------------------------------------------------ #

    async def find(self, filters: AnnonceFiltersDto) -> list[dict[str, Any]]:
        return await self._complete(await self.repository.find(**filters.model_dump()))

    async def find_on_map(self, query: MapQueryDto) -> dict[str, Any]:
        """Annonces d'une commune (`commune_code`) ou de l'emprise affichée.

        Le département concerné (celui de la commune, sinon celui au centre de la carte) est d'abord
        cherché en base ; s'il n'a encore aucune annonce, chaque site est interrogé en tâche de fond
        (statut `pending`) : la réponse est immédiate et les nouvelles annonces arrivent à la demande suivante.
        """
        department = query.department_code or (query.commune_code and department_of(query.commune_code))
        sync = []
        if department:
            sync = [await self._ensure_department(s, department, query.transaction_type) for s in SOURCES.values()]

        zone = (
            {"insee_codes": commune_citycodes(query.commune_code)}
            if query.commune_code
            else {"west": query.west, "east": query.east, "south": query.south, "north": query.north}
        )
        rows = await self.repository.find(
            limit=query.limit + 1,  # une de plus pour savoir si la liste est tronquée
            offset=0,
            transaction_type=query.transaction_type,
            property_type=query.property_type,
            **zone,
        )
        return {"annonces": await self._complete(rows[: query.limit]), "truncated": len(rows) > query.limit, "sync": sync}

    async def _complete(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Nom affichable du site et, pour les annonces enregistrées sans photo, celle de leur fiche (MongoDB)."""
        missing = [(r["source"], r["source_id"]) for r in rows if not r.get("image_url")]
        images = await self.details.first_images(missing)
        for row in rows:
            row["image_url"] = row.get("image_url") or images.get((row["source"], row["source_id"]))
        return _with_labels(rows)

    async def _ensure_department(self, source: ScraperSource, department: str, transaction: TransactionType) -> dict:
        """État du département pour un site, sans jamais attendre le site : si un scraping est nécessaire,
        il est lancé en tâche de fond (`pending`) et la carte affiche déjà les annonces en base."""
        key = (source.name, department, transaction)
        result: dict[str, Any] = {"source": source.name, "source_label": source.label}
        async with _zone_locks[key]:
            if key in _running:
                return {**result, "status": "pending"}
            if key in _finished:  # scraping terminé depuis la dernière demande : on le signale une fois
                return {**result, **_finished.pop(key)}
            if await self.repository.count_in_department(source.name, department, transaction):
                return {**result, "status": "database"}
            if await self.repository.scraped_recently(
                source.name, ZoneLevel.DEPARTEMENT, department, transaction, RETRY_EMPTY_MINUTES, RETRY_ERROR_MINUTES
            ):
                return {**result, "status": "recently_scraped"}

            criteria = SearchCriteria(
                transaction=transaction,
                property_types=(PropertyType.APPARTEMENT, PropertyType.MAISON),
                zone=Zone(ZoneLevel.DEPARTEMENT, code=department),
                sort=SortOrder.RECENTES,
            )
            try:
                _urls(source, criteria, 1)  # zone traduisible par le site ?
            except InvalidCriteria as exc:
                return {**result, "status": "unsupported", "detail": str(exc)}
            _running[key] = asyncio.create_task(self._scrape_in_background(key, source, criteria))
            return {**result, "status": "pending"}

    async def _scrape_in_background(self, key: tuple, source: ScraperSource, criteria: SearchCriteria) -> None:
        try:
            scraped = await self._run(source, criteria, AUTO_SCRAPE_PAGES)
            _finished[key] = {"status": "scraped", "found": scraped["found"]}
        except HTTPException as exc:
            _finished[key] = {"status": "error", "detail": str(exc.detail)}
        except Exception:  # la tâche n'a pas d'appelant pour remonter l'erreur : on la journalise
            logger.exception("Scraping de fond %s", key)
            _finished[key] = {"status": "error", "detail": "Erreur inattendue pendant la récupération des annonces"}
        finally:
            _running.pop(key, None)

    # ------------------------------------------------------------------ #
    # Scraping
    # ------------------------------------------------------------------ #

    async def scrape(self, request: ScrapeRequestDto) -> dict[str, Any]:
        source = _source(request.source)
        criteria = SearchCriteria(
            transaction=request.transaction,
            property_types=tuple(dict.fromkeys(request.property_types)),
            zone=Zone(request.zone.level, request.zone.code, request.zone.place_id),
            sort=request.sort,
        )
        try:
            if request.dry_run:
                return {"source": source.name, "urls": _urls(source, criteria, request.pages)}
            return await self._run(source, criteria, request.pages)
        except InvalidCriteria as exc:
            raise HTTPException(422, str(exc)) from exc

    async def _run(self, source: ScraperSource, criteria: SearchCriteria, pages: int) -> dict[str, Any]:
        """Télécharge, lit et enregistre `pages` pages de résultats ; chaque tentative est journalisée."""
        urls = _urls(source, criteria, pages)  # InvalidCriteria avant tout appel payant
        log = (source.name, criteria.zone.level, criteria.zone.key, criteria.transaction)
        try:
            result = await self._fetch_and_save(source, criteria, urls)
        except HTTPException as exc:
            await self.repository.log_scrape(*log, error=str(exc.detail))
            raise
        await self.repository.log_scrape(*log, found=result["found"])
        return result

    async def _fetch_and_save(self, source: ScraperSource, criteria: SearchCriteria, urls: list[str]) -> dict[str, Any]:
        # Page 1 d'abord : elle indique le nombre total de résultats, donc les pages suivantes utiles.
        first = await self._fetch_page(source, urls[0])
        pages = [first]
        per_page = len(first.listings)
        if per_page and first.total_count is not None:
            urls = urls[: math.ceil(first.total_count / per_page)]  # inutile de payer des pages vides
        elif not per_page:
            urls = urls[:1]
        fetched = [urls[0]]

        # Pages suivantes en parallèle. Une page en échec n'annule pas les autres, déjà payées.
        results = await asyncio.gather(*(self._fetch_page(source, url) for url in urls[1:]), return_exceptions=True)
        for url, result in zip(urls[1:], results):
            if isinstance(result, Exception):
                logger.warning("%s : page ignorée (%s) : %s", source.name, url, getattr(result, "detail", result))
                continue
            pages.append(result)
            fetched.append(url)

        listings: dict[str, Listing] = {}  # par identifiant : une annonce répétée d'une page à l'autre compte une fois
        for page in pages:
            for raw in page.listings:
                listing = normalize(raw, source.name, criteria)
                listings[listing.source_id] = listing
        total_count = first.total_count

        found = list(listings.values())
        geocodage_ids, geocoded = await self.geocoding.geocode([l.address for l in found if l.address])
        inserted, updated = await self.repository.upsert(
            found, [geocodage_ids.get(address_key(l.address)) if l.address else None for l in found]
        )
        logger.info("%s : %d annonces (%d nouvelles, %d mises à jour)", source.name, len(found), inserted, updated)
        return {
            "source": source.name,
            "urls": fetched,
            "total_count": total_count,
            "found": len(found),
            "inserted": inserted,
            "updated": updated,
            "geocoded": geocoded,
        }


    async def _fetch_page(self, source: ScraperSource, url: str) -> ParsedPage:
        html = await self.client.get_page_source(url)
        try:
            return source.parse(html)
        except ParseError as exc:
            raise HTTPException(502, f"{exc} : {url}") from exc


def _source(name: str) -> ScraperSource:
    if name not in SOURCES:
        raise HTTPException(422, f"Source inconnue : {name}. Disponibles : {', '.join(SOURCES)}")
    return SOURCES[name]


def _urls(source: ScraperSource, criteria: SearchCriteria, pages: int) -> list[str]:
    return [source.build_search_url(criteria, page) for page in range(1, pages + 1)]


def _with_labels(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ajoute le nom affichable du site d'origine."""
    for row in rows:
        source = SOURCES.get(row["source"])
        row["source_label"] = source.label if source else row["source"]
    return rows


AnnoncesServiceDep = Annotated[AnnoncesService, Depends(AnnoncesService)]
