"""Récupération brute (aucune transformation) des sources du module géo."""

import json

from ...geo_utils import square_geojson
from ...http_client import http
from ...open_data import tabular_query

BAN_BASE = "https://data.geopf.fr/geocodage"
GEO_API_BASE = "https://geo.api.gouv.fr"
GEO_API_FIELDS = "nom,code,codesPostaux,codeDepartement,codeRegion,departement,region,codeEpci,population,surface,centre"
CADASTRE_URL = "https://apicarto.ign.fr/api/cadastre/parcelle"
GPU_BASE = "https://apicarto.ign.fr/api/gpu"
# Liste des immeubles protégés MH (Ministère de la Culture). data.culture.gouv.fr a migré (redirection vers
# culture.data.gouv.fr, sans API Opendatasoft) : on interroge la même ressource publiée sur data.gouv.fr via l'API tabulaire.
MONUMENTS_RESOURCE_ID = "3a52af4a-f9da-4dcc-8110-b07774dfb3bc"


async def ban_search(q: str, *, limit: int = 5) -> list[dict]:
    res = await http.get(f"{BAN_BASE}/search", source="ban", params={"q": q, "limit": limit, "index": "address"})
    return res.get("features") or []


async def ban_reverse(p: dict, limit: int = 1) -> list[dict]:
    res = await http.get(
        f"{BAN_BASE}/reverse", source="ban", params={"lat": p["lat"], "lon": p["lon"], "limit": limit, "index": "address"}
    )
    return res.get("features") or []


async def geo_api_commune(insee: str) -> dict | None:
    params = {"code": insee, "fields": GEO_API_FIELDS, "format": "json"}
    res = await http.get(f"{GEO_API_BASE}/communes", source="geo_api", params=params)
    if not res:
        # Paris, Lyon, Marseille : la BAN rattache l'adresse à l'arrondissement (75102), absent de la liste des communes.
        res = await http.get(f"{GEO_API_BASE}/communes", source="geo_api", params={**params, "type": "arrondissement-municipal"})
    return res[0] if res else None


async def geo_api_communes_of_department(dep: str) -> list[dict]:
    return await http.get(
        f"{GEO_API_BASE}/departements/{dep}/communes", source="geo_api", params={"fields": GEO_API_FIELDS, "format": "json"}
    )


async def cadastre_parcels_around(p: dict, half_side_m: float = 6) -> list[dict]:
    """L'API ne renvoie rien pour une géométrie Point : on interroge avec un carré de quelques mètres."""
    res = await http.get(
        CADASTRE_URL, source="apicarto_cadastre", params={"geom": json.dumps(square_geojson(p, half_side_m)), "_limit": 50}
    )
    return res.get("features") or []


async def cadastre_parcel_by_idu(idu: str) -> dict | None:
    res = await http.get(
        CADASTRE_URL,
        source="apicarto_cadastre",
        params={"code_insee": idu[:5], "com_abs": idu[5:8], "section": idu[8:10], "numero": idu[10:14]},
    )
    return next((f for f in res.get("features") or [] if (f.get("properties") or {}).get("idu") == idu), None)


async def gpu_layer(layer: str, geometry: dict) -> list[dict]:
    """Objets d'une couche GPU (zone-urba, prescription-surf/lin/pct, assiette-sup-s) intersectant une géométrie GeoJSON."""
    res = await http.get(f"{GPU_BASE}/{layer}", source="apicarto_gpu", params={"geom": json.dumps(geometry)}, timeout_ms=60000)
    return res.get("features") or []


async def monuments_by_commune(insee: str) -> list[dict]:
    return await tabular_query("monuments", MONUMENTS_RESOURCE_ID, {"COG_Insee_lors_de_la_protection": insee}, max_rows=500)
