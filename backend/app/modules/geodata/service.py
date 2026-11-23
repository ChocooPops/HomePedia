import asyncio
import logging
import re
import unicodedata
from typing import Annotated, Any, Callable

import httpx
from fastapi import Depends, HTTPException
from pymongo import UpdateOne
from sqlalchemy import text

from app.core.database import MongoDb, PgEngine

ETALAB_URL = "https://etalab-datasets.geo.data.gouv.fr/contours-administratifs/2024/geojson"
REGIONS_URL = f"{ETALAB_URL}/regions-1000m.geojson"
DEPARTMENTS_URL = f"{ETALAB_URL}/departements-1000m.geojson"
COMMUNES_URL = f"{ETALAB_URL}/communes-1000m.geojson"

# Géocodeur de la Géoplateforme IGN (successeur d'api-adresse.data.gouv.fr), sans clé d'API.
GEOCODER_URL = "https://data.geopf.fr/geocodage/search"

# Nombre maximal de résultats par type dans la recherche.
SEARCH_LIMITS = {"region": 3, "department": 3, "commune": 6, "address": 5}
# Score minimal (0 à 1) d'une adresse renvoyée par le géocodeur.
ADDRESS_MIN_SCORE = 0.5

logger = logging.getLogger(__name__)

Row = dict[str, Any]


class GeoDataService:
    """Régions, départements et communes, avec leurs contours.

    Au premier appel, chaque jeu de données est téléchargé depuis Etalab puis enregistré :
    PostgreSQL stocke les codes et les noms, MongoDB y ajoute les coordonnées du contour.
    Les réponses sont lues dans MongoDB.
    """

    def __init__(self, pg: PgEngine, mongo: MongoDb):
        self.pg = pg
        self.mongo = mongo

    async def get_regions(self) -> list[Row]:
        await self._ensure_regions()
        return await self.mongo.regions.find({}, {"_id": 0}).sort("code", 1).to_list()

    async def get_departments_by_region(self, region_code: str) -> list[Row]:
        await self._ensure_departments()
        departments = await self.mongo.departments.find({"region_code": region_code}, {"_id": 0}).sort("code", 1).to_list()
        if not departments:
            raise HTTPException(404, f"Aucun département pour la région {region_code}")
        return departments

    async def get_communes_by_department(self, department_code: str) -> list[Row]:
        await self._ensure_communes()
        communes = await self.mongo.communes.find(
            {"department_code": department_code.upper()}, {"_id": 0}
        ).sort("code", 1).to_list()
        if not communes:
            raise HTTPException(404, f"Aucune commune pour le département {department_code}")
        return communes

    # ------------------------------------------------------------------ #
    # Recherche
    # ------------------------------------------------------------------ #

    async def search(self, query: str) -> list[Row]:
        """Régions, départements, communes (par nom ou code), puis adresses."""
        query = query.strip()
        await self._ensure_communes()
        areas, addresses = await asyncio.gather(self._search_areas(query), self._search_addresses(query))
        # « Paris », « Bretagne »… : le territoire suffit, les voies homonymes ne seraient que du bruit.
        # Une saisie avec un chiffre (« 10 rue de Paris ») vise en revanche une adresse.
        exact_area = any(_normalize(a["name"]) == _normalize(query) for a in areas)
        if exact_area and not any(c.isdigit() for c in query):
            addresses = []
        return areas + addresses

    async def _search_areas(self, query: str) -> list[Row]:
        region_names = await self._names("regions")
        department_names = await self._names("departments")
        # Pas de recherche par code pour les régions : leurs codes (11, 75…) se confondent avec ceux des départements.
        searches = [
            ("region", "regions", False, lambda d: None),
            ("department", "departments", True, lambda d: f"{d['code']} · {region_names.get(d['region_code'], '')}"),
            (
                "commune",
                "communes",
                True,
                lambda d: f"{department_names.get(d['department_code'], '')} ({d['department_code']})",
            ),
        ]
        results: list[Row] = []
        for kind, collection, by_code, context in searches:
            for doc in await self._find_by_name_or_code(collection, query, SEARCH_LIMITS[kind], by_code):
                results.append(
                    {
                        "kind": kind,
                        "code": doc["code"],
                        "name": doc["name"],
                        "context": context(doc),
                        "bbox": _bbox(doc["coordinates"]),
                    }
                )
        return results

    async def _names(self, collection: str) -> dict[str, str]:
        docs = await self.mongo[collection].find({}, {"_id": 0, "code": 1, "name": 1}).to_list()
        return {d["code"]: d["name"] for d in docs}

    async def _find_by_name_or_code(self, collection: str, query: str, limit: int, by_code: bool) -> list[Row]:
        """Classement : code ou nom exact, puis nom commençant par la saisie, puis la contenant ; les plus courts d'abord."""
        pattern = _name_pattern(query)
        code = query.upper() if by_code else None
        ranked = await (
            await self.mongo[collection].aggregate(
                [
                    {"$match": {"$or": [{"name": {"$regex": pattern, "$options": "i"}}, {"code": code}]}},
                    {"$project": {"_id": 0, "code": 1, "name": 1}},
                    {
                        "$addFields": {
                            "rank": {
                                "$switch": {
                                    "branches": [
                                        {"case": {"$eq": ["$code", code]}, "then": 0},
                                        {"case": _regex_match(f"^{pattern}$"), "then": 0},
                                        {"case": _regex_match(f"^{pattern}"), "then": 1},
                                    ],
                                    "default": 2,
                                }
                            },
                            "length": {"$strLenCP": "$name"},
                        }
                    },
                    {"$sort": {"rank": 1, "length": 1, "name": 1}},
                    {"$limit": limit},
                ]
            )
        ).to_list()
        codes = [d["code"] for d in ranked]
        docs = {d["code"]: d for d in await self.mongo[collection].find({"code": {"$in": codes}}, {"_id": 0}).to_list()}
        return [docs[c] for c in codes if c in docs]

    @staticmethod
    async def _search_addresses(query: str) -> list[Row]:
        """Adresses et voies via le géocodeur IGN. En cas d'indisponibilité, la recherche continue sans elles."""
        if len(query) < 3:  # minimum exigé par le géocodeur
            return []
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(GEOCODER_URL, params={"q": query, "limit": 10})
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Géocodeur indisponible : %s", exc)
            return []

        results: list[Row] = []
        seen: set[str] = set()
        for feature in response.json().get("features", []):
            props = feature["properties"]
            # Seulement les numéros et les voies : communes et lieux-dits sont couverts ou trop ambigus.
            if props.get("type") not in ("housenumber", "street") or props.get("score", 0) < ADDRESS_MIN_SCORE:
                continue
            if props["label"] in seen:
                continue
            seen.add(props["label"])
            lon, lat = feature["geometry"]["coordinates"]
            results.append(
                {
                    "kind": "address",
                    "code": None,
                    "name": props["label"],
                    "context": props.get("context"),
                    "bbox": [lon, lat, lon, lat],
                }
            )
        return results[: SEARCH_LIMITS["address"]]

    # ------------------------------------------------------------------ #
    # Chargement depuis Etalab (parents d'abord, pour les clés étrangères)
    # ------------------------------------------------------------------ #

    async def _ensure_regions(self) -> None:
        await self._ensure_loaded(
            "regions",
            REGIONS_URL,
            pg_columns=["code", "name"],
            to_row=lambda p: {"code": p["code"], "name": p["nom"]},
        )

    async def _ensure_departments(self) -> None:
        await self._ensure_regions()
        await self._ensure_loaded(
            "departments",
            DEPARTMENTS_URL,
            pg_columns=["code", "name", "region_code"],
            to_row=lambda p: {"code": p["code"], "name": p["nom"], "region_code": p["region"]},
        )

    async def _ensure_communes(self) -> None:
        await self._ensure_departments()
        await self._ensure_loaded(
            "communes",
            COMMUNES_URL,
            pg_columns=["code", "name", "department_code"],
            to_row=lambda p: {"code": p["code"], "name": p["nom"], "department_code": p["departement"]},
        )

    async def _ensure_loaded(
        self,
        table: str,
        url: str,
        pg_columns: list[str],
        to_row: Callable[[dict[str, Any]], Row],
    ) -> None:
        """Télécharge et enregistre le jeu de données si la table ou la collection est vide."""
        async with self.pg.connect() as conn:
            pg_count = (await conn.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one()
        mongo_count = await self.mongo[table].estimated_document_count()
        if pg_count and mongo_count:
            return

        rows = [
            {**to_row(f["properties"]), "coordinates": _as_multipolygon(f["geometry"])}
            for f in await self._fetch_features(url)
        ]

        # Insère seulement les lignes absentes : celles déjà présentes sont conservées.
        async with self.pg.begin() as conn:
            await conn.execute(
                text(
                    f"INSERT INTO {table} ({', '.join(pg_columns)}) "
                    f"VALUES ({', '.join(':' + c for c in pg_columns)}) ON CONFLICT (code) DO NOTHING"
                ),
                [{c: r[c] for c in pg_columns} for r in rows],
            )
        await self.mongo[table].bulk_write(
            [UpdateOne({"code": r["code"]}, {"$setOnInsert": r}, upsert=True) for r in rows],
            ordered=False,
        )

    @staticmethod
    async def _fetch_features(url: str) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            response = await client.get(url)
        response.raise_for_status()
        return response.json()["features"]


def _as_multipolygon(geometry: dict[str, Any]) -> list:
    """Coordonnées toujours au format MultiPolygon (un Polygon devient une liste d'un polygone)."""
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"]]
    return geometry["coordinates"]


# Lettres équivalentes pour une recherche insensible aux accents (et à la casse, avec l'option "i").
_ACCENTS = {
    "a": "aàâäAÀÂÄ",
    "c": "cçCÇ",
    "e": "eéèêëEÉÈÊË",
    "i": "iîïIÎÏ",
    "o": "oôöOÔÖ",
    "u": "uùûüUÙÛÜ",
    "y": "yÿYŸ",
}
_SEPARATORS = re.compile(r"[\s'’-]+")


def _normalize(text: str) -> str:
    """Minuscules, sans accents, séparateurs remplacés par des espaces."""
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(w for w in _SEPARATORS.split(text) if w)


def _name_pattern(query: str) -> str:
    """Regex qui ignore accents, casse et séparateurs : « saint etienne » trouve « Saint-Étienne »."""
    words = _normalize(query).split(" ")
    return r"[\s'’-]+".join(
        "".join(f"[{_ACCENTS[c]}]" if c in _ACCENTS else re.escape(c) for c in word) for word in words
    )


def _regex_match(regex: str) -> dict[str, Any]:
    return {"$regexMatch": {"input": "$name", "regex": regex, "options": "i"}}


def _bbox(coordinates: list) -> list[float]:
    """Emprise [lon_min, lat_min, lon_max, lat_max] des anneaux extérieurs d'un MultiPolygon."""
    points = [point for polygon in coordinates for point in polygon[0]]
    lons = [p[0] for p in points]
    lats = [p[1] for p in points]
    return [min(lons), min(lats), max(lons), max(lats)]


GeoDataServiceDep = Annotated[GeoDataService, Depends(GeoDataService)]
