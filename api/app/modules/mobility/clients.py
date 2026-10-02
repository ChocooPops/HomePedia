"""Récupération brute (aucune transformation) des sources de mobilité."""

from ...http_client import http
from ...open_data import overpass_query, tabular_query

# Base nationale IRVE consolidée (ressource « dernière version du schéma »).
IRVE_RESOURCE_ID = "eb76d20a-8501-400e-b336-d85724de5435"
# Base nationale des lieux de stationnement (hors voirie, non exhaustive).
BNLS_RESOURCE_ID = "e32f7675-913b-4e01-b8c8-0a29733e4407"
TRANSPORT_DATASETS_URL = "https://transport.data.gouv.fr/api/datasets"


async def irve_by_commune(insee: str) -> list[dict]:
    return await tabular_query("irve", IRVE_RESOURCE_ID, {"code_insee_commune": insee}, max_rows=2000)


async def bnls_by_commune(insee: str) -> list[dict]:
    return await tabular_query("bnls", BNLS_RESOURCE_ID, {"insee": insee}, max_rows=500)


async def osm_stops_and_cycleways(p: dict, stops_radius_m: int, cycle_radius_m: int) -> list[dict]:
    lat, lon = p["lat"], p["lon"]
    return await overpass_query(f"""[out:json][timeout:60];
(
  nwr(around:{stops_radius_m},{lat},{lon})[highway=bus_stop];
  nwr(around:{stops_radius_m},{lat},{lon})[railway~"^(station|halt|tram_stop)$"];
)->.stops;
.stops out center tags;
way(around:{cycle_radius_m},{lat},{lon})[highway=cycleway]->.cw;
way(around:{cycle_radius_m},{lat},{lon})[~"^cycleway(:both|:left|:right)?$"~"^(lane|track)$"]->.lanes;
(.cw; .lanes;);
out geom tags;""")


async def transport_datasets() -> list[dict]:
    return await http.get(TRANSPORT_DATASETS_URL, source="transport_gouv", timeout_ms=60000)
