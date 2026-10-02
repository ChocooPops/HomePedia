"""Récupération brute (aucune transformation) : Hub'Eau (eau potable, nappes) et VigiEau (sécheresse)."""

from ...geo_utils import bbox_around
from ...http_client import http

# Paramètres suivis (codes SANDRE).
WATER_PARAMETERS: dict[str, str] = {
    "1340": "nitrates",
    "6276": "total_pesticides",
    "1345": "hardness",
    "8847": "pfas_sum_20",
    "9268": "pfas_sum_4",
}

HUBEAU_BASE = "https://hubeau.eaufrance.fr/api/v1"
VIGIEAU_BASE = "https://api.vigieau.gouv.fr/api"


async def drinking_water(insee: str, since_iso: str, max_rows: int = 1000) -> list[dict]:
    """Résultats d'analyse au robinet (réseau de distribution) d'une commune, les plus récents d'abord."""
    out: list[dict] = []
    url: str | None = f"{HUBEAU_BASE}/qualite_eau_potable/resultats_dis"
    params: dict | None = {
        "code_commune": insee,
        "code_parametre": ",".join(WATER_PARAMETERS),
        "date_min_prelevement": since_iso,
        "size": 500,
        "sort": "desc",
    }
    while url and len(out) < max_rows:
        # Hub'Eau répond 206 pour une page partielle ; l'URL « next » porte déjà tous les paramètres.
        res = await http.get(url, source="hubeau_eau_potable", params=params, allow_statuses=(206,))
        out.extend(res.get("data") or [])
        url = res.get("next")
        params = None
    return out


async def groundwater_stations(p: dict, radius_m: float) -> list[dict]:
    b = bbox_around(p, radius_m)
    res = await http.get(
        f"{HUBEAU_BASE}/niveaux_nappes/stations",
        source="hubeau_nappes",
        params={"bbox": f"{b['minLon']},{b['minLat']},{b['maxLon']},{b['maxLat']}", "size": 200},
        allow_statuses=(206,),
    )
    return res.get("data") or []


async def last_groundwater_measure(code_bss: str) -> dict | None:
    res = await http.get(
        f"{HUBEAU_BASE}/niveaux_nappes/chroniques",
        source="hubeau_nappes",
        params={"code_bss": code_bss, "size": 1, "sort": "desc"},
        allow_statuses=(206,),
    )
    data = res.get("data") or []
    return data[0] if data else None


async def vigieau_zones(p: dict, insee: str, zone_type: str) -> list[dict]:
    """Zones d'alerte et restrictions en vigueur. zone_type : SUP (superficiel), SOU (souterrain), AEP (eau potable)."""
    res = await http.get(
        f"{VIGIEAU_BASE}/zones",
        source="vigieau",
        params={"lon": p["lon"], "lat": p["lat"], "commune": insee, "profil": "particulier", "zoneType": zone_type},
        allow_statuses=(404,),
    )
    return res if isinstance(res, list) else []
