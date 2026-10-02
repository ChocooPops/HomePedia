"""Récupération brute du référentiel territorial : API Géo, contours france-geojson, DVF par département."""

import csv
import gzip
import io

from ...http_client import http
from ..building.clients import DVF_BASE
from ..geo.clients import GEO_API_BASE

FRANCE_GEOJSON_BASE = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master"
FRANCE_GEOJSON_FILES = {"region": "regions-version-simplifiee.geojson", "department": "departements-version-simplifiee.geojson"}


async def geo_api_regions() -> list[dict]:
    return await http.get(f"{GEO_API_BASE}/regions", source="geo_api", params={"fields": "nom,code"})


async def geo_api_departments() -> list[dict]:
    return await http.get(f"{GEO_API_BASE}/departements", source="geo_api", params={"fields": "nom,code,codeRegion"})


async def france_geojson(level: str) -> list[dict]:
    """Contours simplifiés des régions ou des départements (features GeoJSON, propriétés « code » et « nom »)."""
    res = await http.get(f"{FRANCE_GEOJSON_BASE}/{FRANCE_GEOJSON_FILES[level]}", source="france_geojson", timeout_ms=60000)
    return res.get("features") or []


async def geo_api_commune_contours(dep: str) -> list[dict]:
    """Contours de toutes les communes d'un département (features GeoJSON)."""
    res = await http.get(
        f"{GEO_API_BASE}/departements/{dep}/communes",
        source="geo_api",
        params={"format": "geojson", "geometry": "contour", "fields": "nom,code,population"},
        timeout_ms=120000,
    )
    return res.get("features") or []


async def geo_api_commune_contour(insee: str) -> dict | None:
    res = await http.get(
        f"{GEO_API_BASE}/communes/{insee}", source="geo_api", params={"fields": "nom,code,population,contour", "format": "json"},
        allow_statuses=(404,),
    )
    return res if isinstance(res, dict) and res.get("contour") else None


async def dvf_department_year(dep: str, year: int) -> list[dict[str, str]]:
    """Fichier DVF géolocalisé d'un département pour une année (CSV compressé)."""
    res = await http.request(
        "GET", f"{DVF_BASE}/{year}/departements/{dep}.csv.gz", source="dvf", binary=True, allow_statuses=(404,), timeout_ms=300000
    )
    if res.status == 404:
        return []
    text = gzip.decompress(res.data).decode("utf-8")
    return list(csv.DictReader(io.StringIO(text, newline="")))
