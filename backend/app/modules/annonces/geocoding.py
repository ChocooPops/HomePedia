import asyncio
import logging
import re
import unicodedata
from typing import Annotated, Any

import httpx
from fastapi import Depends
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import PgEngine

logger = logging.getLogger(__name__)

# Requêtes simultanées vers le géocodeur (limité à 50 requêtes par seconde et par IP).
CONCURRENCY = 5


class GeocodingService:
    """Géocode des adresses via la Géoplateforme IGN, avec la table `geocodage` comme cache.

    Une adresse déjà présente (même adresse normalisée) n'est jamais renvoyée au géocodeur.
    """

    def __init__(self, pg: PgEngine) -> None:
        self.pg = pg
        self.url = get_settings().geocoding_url

    async def geocode(self, addresses: list[str]) -> tuple[dict[str, int], int]:
        """Identifiants `geocodage.id` par clé d'adresse (address_key), et nombre d'adresses nouvellement géocodées."""
        queries = {address_key(a): a for a in addresses if a}
        if not queries:
            return {}, 0

        known = await self._ids(list(queries))
        missing = {k: q for k, q in queries.items() if k not in known}
        rows: list[dict[str, Any]] = []
        if missing:
            semaphore = asyncio.Semaphore(CONCURRENCY)
            async with httpx.AsyncClient(timeout=10) as client:
                results = await asyncio.gather(*(self._lookup(client, semaphore, q) for q in missing.values()))
            # Une erreur réseau (None) n'est pas enregistrée : l'adresse sera retentée au prochain scraping.
            rows = [{"address_key": k, "query": q, **r} for (k, q), r in zip(missing.items(), results) if r is not None]
            if rows:
                async with self.pg.begin() as conn:
                    await conn.execute(_INSERT, rows)
            known |= await self._ids(list(missing))

        return known, len(rows)

    async def _ids(self, keys: list[str]) -> dict[str, int]:
        async with self.pg.connect() as conn:
            result = await conn.execute(
                text("SELECT address_key, id FROM geocodage WHERE address_key = ANY(:keys)"), {"keys": keys}
            )
            return {key: id_ for key, id_ in result}

    async def _lookup(self, client: httpx.AsyncClient, semaphore: asyncio.Semaphore, query: str) -> dict | None:
        """Meilleur résultat du géocodeur ; un dictionnaire de valeurs vides si l'adresse est introuvable."""
        params: dict[str, Any] = {"q": query, "limit": 1}
        if postcode := re.search(r"\b\d{5}\b", query):
            params["postcode"] = postcode.group()
        try:
            async with semaphore:
                response = await client.get(self.url, params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Géocodage impossible pour %r : %s", query, exc)
            return None

        features = response.json().get("features") or []
        if not features:
            return dict.fromkeys(_RESULT_COLUMNS)
        props = features[0]["properties"]
        longitude, latitude = features[0]["geometry"]["coordinates"]
        return {
            "label": props.get("label"),
            "score": props.get("score"),
            "result_type": props.get("type"),
            "housenumber": props.get("housenumber"),
            "street": props.get("street"),
            "postcode": props.get("postcode"),
            "city": props.get("city"),
            "citycode": props.get("citycode"),
            "latitude": latitude,
            "longitude": longitude,
        }


_RESULT_COLUMNS = [
    "label",
    "score",
    "result_type",
    "housenumber",
    "street",
    "postcode",
    "city",
    "citycode",
    "latitude",
    "longitude",
]
_COLUMNS = ["address_key", "query", *_RESULT_COLUMNS]
_INSERT = text(
    f"INSERT INTO geocodage ({', '.join(_COLUMNS)}) VALUES ({', '.join(':' + c for c in _COLUMNS)}) "
    "ON CONFLICT (address_key) DO NOTHING"
)


def address_key(address: str) -> str:
    """Adresse normalisée (minuscules, sans accents ni ponctuation) servant de clé de cache."""
    address = unicodedata.normalize("NFD", address.lower())
    address = "".join(c for c in address if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w]+", " ", address).split())


GeocodingServiceDep = Annotated[GeocodingService, Depends(GeocodingService)]
