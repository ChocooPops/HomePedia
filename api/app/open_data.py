"""
Clients génériques pour les grandes familles de portails open data.
Ils gèrent la pagination ; la normalisation reste dans chaque module.
"""

from urllib.parse import urlencode

from .http_client import http

TABULAR_BASE = "https://tabular-api.data.gouv.fr/api/resources"
OVERPASS_ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
WFS_URL = "https://data.geopf.fr/wfs/ows"


async def tabular_query(
    source: str,
    resource_id: str,
    filters: dict,
    *,
    page_size: int = 50,
    max_rows: int = 1000,
    extra: dict | None = None,
) -> list[dict]:
    """
    API tabulaire data.gouv.fr : interroge un CSV publié sans le télécharger.
    `filters` : colonne -> valeur exacte (traduit en `col__exact=valeur`).
    """
    params = {"page_size": min(page_size, 50), **(extra or {})}
    params |= {f"{k}__exact": v for k, v in filters.items()}
    rows: list[dict] = []
    url = f"{TABULAR_BASE}/{resource_id}/data/"
    first = True
    while url and len(rows) < max_rows:
        page = await http.get(url, source=source, limiter_key="tabular", params=params if first else None)
        rows.extend(page.get("data") or [])
        url = (page.get("links") or {}).get("next")
        first = False
    return rows[:max_rows]


async def ods_records(source: str, base_url: str, dataset: str, params: dict, max_records: int = 100) -> list[dict]:
    """API Explore v2.1 des portails Opendatasoft (data.education, data.economie, GRDF...)."""
    out: list[dict] = []
    limit = min(100, max_records)
    offset = 0
    while offset < max_records and offset < 10000:
        page = await http.get(
            f"{base_url}/catalog/datasets/{dataset}/records", source=source, params={**params, "limit": limit, "offset": offset}
        )
        results = page.get("results") or []
        out.extend(results)
        if len(results) < limit or len(out) >= (page.get("total_count") or 0):
            break
        offset += limit
    return out[:max_records]


async def datafair_lines(source: str, dataset_url: str, params: dict, max_rows: int = 100) -> list[dict]:
    """API data-fair (ADEME, Enedis)."""
    out: list[dict] = []
    url = f"{dataset_url}/lines"
    first = True
    while url and len(out) < max_rows:
        page = await http.get(url, source=source, params={"size": min(max_rows, 1000), **params} if first else None)
        out.extend(page.get("results") or [])
        url = page.get("next")
        first = False
    return out[:max_rows]


async def overpass_query(ql: str) -> list[dict]:
    """
    OpenStreetMap Overpass. Le serveur principal renvoie 406 si le User-Agent est absent ou factice,
    et 504 quand il est saturé : on bascule alors sur un miroir public.
    """
    body = urlencode({"data": ql})
    last_error: Exception | None = None
    for url in OVERPASS_ENDPOINTS:
        try:
            res = await http.post(
                url, body, source="overpass",
                headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "*/*"}, timeout_ms=90000,
            )
            return res.get("elements") or []
        except Exception as err:  # noqa: BLE001 - on tente le miroir quelle que soit l'erreur
            last_error = err
    raise last_error


async def wfs_features(type_name: str, bbox: dict, count: int = 200) -> list[dict]:
    """WFS de la Géoplateforme IGN (GeoJSON, WGS84)."""
    res = await http.get(
        WFS_URL,
        source="geopf_wfs",
        params={
            "SERVICE": "WFS",
            "VERSION": "2.0.0",
            "REQUEST": "GetFeature",
            "TYPENAMES": type_name,
            "OUTPUTFORMAT": "application/json",
            "SRSNAME": "EPSG:4326",
            "COUNT": count,
            # En WFS 2.0 + EPSG:4326, l'ordre des axes du BBOX est lat,lon.
            "BBOX": f"{bbox['minLat']},{bbox['minLon']},{bbox['maxLat']},{bbox['maxLon']},urn:ogc:def:crs:EPSG::4326",
        },
    )
    return res.get("features") or []
