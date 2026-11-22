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


GeoDataServiceDep = Annotated[GeoDataService, Depends(GeoDataService)]
