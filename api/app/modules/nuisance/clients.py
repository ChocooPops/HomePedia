"""Récupération brute des sources du module nuisances : Overpass (OSM) et OpenSky."""

import re
from collections.abc import Callable

from ...geo_utils import bbox_around
from ...http_client import http
from ...open_data import overpass_query

# Catégorisation des objets OSM « source de nuisance ».
# L'ordre compte : la première règle qui correspond l'emporte.
POI_RULES: list[tuple[str, Callable[[dict], bool]]] = [
    ("nightlife", lambda t: bool(re.match(r"^(bar|pub|nightclub)$", t.get("amenity") or ""))),
    ("concert_venue", lambda t: bool(re.match(r"^(music_venue|theatre|events_venue|arts_centre)$", t.get("amenity") or ""))),
    ("stadium", lambda t: t.get("leisure") == "stadium" or t.get("building") == "stadium"),
    ("marketplace", lambda t: t.get("amenity") == "marketplace"),
    ("place_of_worship", lambda t: t.get("amenity") == "place_of_worship"),
    ("wastewater_plant", lambda t: t.get("man_made") == "wastewater_plant"),
    ("grain_silo", lambda t: t.get("man_made") == "silo"),
    ("farm", lambda t: t.get("landuse") == "farmyard"),
    ("landfill", lambda t: t.get("landuse") == "landfill" or t.get("amenity") == "waste_transfer_station"),
    ("industrial", lambda t: t.get("landuse") == "industrial"),
    ("wind_turbine", lambda t: t.get("generator:source") == "wind"),
    ("airport", lambda t: t.get("aeroway") == "aerodrome"),
]

LINE_RULES: list[tuple[str, Callable[[dict], bool]]] = [
    ("power_line", lambda t: t.get("power") == "line"),
    ("railway", lambda t: t.get("railway") == "rail"),
    ("major_road", lambda t: bool(re.match(r"^(motorway|trunk)$", t.get("highway") or ""))),
]


async def around(p: dict, radius_m: int, wide_radius_m: int) -> dict:
    """Objets OSM autour du point : { "pois": [...], "lines": [...] }."""
    a = f"around:{radius_m},{p['lat']},{p['lon']}"
    w = f"around:{wide_radius_m},{p['lat']},{p['lon']}"
    ql = f"""[out:json][timeout:60];
(
  nwr({a})[amenity~"^(bar|pub|nightclub|music_venue|theatre|events_venue|arts_centre|marketplace|place_of_worship|waste_transfer_station)$"];
  nwr({a})[leisure=stadium];
  nwr({a})[man_made~"^(wastewater_plant|silo)$"];
  nwr({a})[landuse~"^(farmyard|industrial|landfill)$"];
  nwr({w})["generator:source"=wind];
  nwr({w})[aeroway=aerodrome];
)->.pois;
.pois out center tags;
(
  way({w})[power=line];
  way({a})[railway=rail];
  way({a})[highway~"^(motorway|trunk)$"];
)->.lines;
.lines out geom tags;"""
    elements = await overpass_query(ql)
    return {
        "pois": [e for e in elements if e.get("geometry") is None],
        "lines": [e for e in elements if e.get("type") == "way" and e.get("geometry") is not None],
    }


async def states(p: dict, radius_m: int) -> dict:
    """Instantané des aéronefs dans une boîte autour du point (accès anonyme, quota limité)."""
    b = bbox_around(p, radius_m)
    res = await http.get(
        "https://opensky-network.org/api/states/all",
        source="opensky",
        params={"lamin": b["minLat"], "lomin": b["minLon"], "lamax": b["maxLat"], "lomax": b["maxLon"]},
    )
    return {"time": res.get("time"), "states": res.get("states") or []}
