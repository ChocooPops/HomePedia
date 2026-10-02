"""Normalisation des objets OSM, des arrêtés PEB et des états OpenSky en lignes de base."""

import math
import re
from datetime import UTC, datetime

from ...geo_utils import geojson_to_wkt, haversine_meters, point_wkt
from ...parse import js_round, num, str_
from .clients import LINE_RULES, POI_RULES

KEPT_TAGS = [
    "name", "amenity", "leisure", "man_made", "landuse", "opening_hours", "voltage", "operator", "religion", "bells",
    "highway", "railway", "aeroway",
]

_JS_DECIMAL = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")


def pick_tags(t: dict | None) -> dict:
    return {k: v for k, v in (t or {}).items() if k in KEPT_TAGS}


def _first(*values):
    """Équivalent de `a ?? b ?? c` : première valeur non nulle."""
    return next((v for v in values if v is not None), None)


def _kilovolts(voltage: str) -> str:
    """Première tension de la liste, en kV (« 20000;400 » -> « 20 kV ») ; une tension illisible donne « NaN kV »."""
    s = voltage.split(";")[0].strip()
    if s == "":
        n = 0.0
    elif _JS_DECIMAL.match(s):
        n = float(s)
    elif re.match(r"^[+-]?Infinity$", s):
        n = -math.inf if s.startswith("-") else math.inf
    elif re.match(r"^0[xX][0-9a-fA-F]+$|^0[oO][0-7]+$|^0[bB][01]+$", s):
        n = float(int(s, 0))
    else:
        n = math.nan
    if math.isnan(n):
        return "NaN kV"
    if math.isinf(n):
        return f"{'-' if n < 0 else ''}Infinity kV"
    return f"{js_round(n / 1000)} kV"


def normalize_poi(e: dict, stamp: dict) -> dict | None:
    t = e.get("tags") or {}
    category = next((c for c, match in POI_RULES if match(t)), None)
    center = e.get("center") or {}
    lat = _first(e.get("lat"), center.get("lat"))
    lon = _first(e.get("lon"), center.get("lon"))
    if category is None or lat is None or lon is None:
        return None
    return {
        "externalId": f"osm:{e['type']}/{e['id']}",
        "category": category,
        "subcategory": str_(_first(t.get("amenity"), t.get("leisure"), t.get("man_made"), t.get("landuse"), t.get("aeroway")), 80),
        "name": str_(t.get("name"), 255),
        "tags": pick_tags(t),
        "latitude": lat,
        "longitude": lon,
        "location": point_wkt(lon, lat),
        **stamp,
    }


def normalize_line(e: dict, stamp: dict) -> dict | None:
    t = e.get("tags") or {}
    category = next((c for c, match in LINE_RULES if match(t)), None)
    geometry = e.get("geometry")
    if category is None or not geometry or len(geometry) < 2:
        return None
    voltage = t.get("voltage")
    return {
        "externalId": f"osm:way/{e['id']}",
        "category": category,
        "subcategory": str_(_kilovolts(voltage) if voltage else _first(t.get("highway"), t.get("railway")), 80),
        "name": str_(_first(t.get("name"), t.get("ref")), 255),
        "tags": pick_tags(t),
        "geom": geojson_to_wkt({"type": "LineString", "coordinates": [[g["lon"], g["lat"]] for g in geometry]}),
        **stamp,
    }


def normalize_peb(f: dict, stamp: dict) -> dict:
    """Aérodrome doté d'un plan d'exposition au bruit (couche DGAC : point + arrêté)."""
    props = f.get("properties") or {}
    lon, lat = f["geometry"]["coordinates"][:2]
    return {
        "externalId": f"peb:{_first(props.get('oaci'), f.get('id'))}",
        "category": "airport_noise_plan",
        "subcategory": str_(props.get("oaci"), 80),
        "name": str_(props.get("nom"), 255),
        "tags": {"arrete": props["arrete_peb"]} if "arrete_peb" in props else {},
        "latitude": lat,
        "longitude": lon,
        "location": point_wkt(lon, lat),
        **stamp,
    }


def observed_at(time: float | None) -> datetime | None:
    """Horodatage OpenSky (secondes Unix) -> datetime UTC sans fuseau."""
    return None if time is None else datetime.fromtimestamp(time, UTC).replace(tzinfo=None)


def normalize_flight(s: list, address_id: int, p: dict, at: datetime | None, stamp: dict) -> dict:
    """Vecteur d'état OpenSky : [0] icao24, [1] indicatif, [2] pays, [5] lon, [6] lat, [7] altitude baro, [8] au sol, [9] vitesse, [13] altitude géo."""
    return {
        "addressId": address_id,
        "observedAt": at,
        "icao24": str(s[0]),
        "callsign": str_(s[1], 12),
        "originCountry": str_(s[2], 64),
        "altitudeM": num(_first(s[7], s[13] if len(s) > 13 else None)),
        "onGround": bool(s[8]),
        "velocityMs": num(s[9]),
        "distanceM": js_round(haversine_meters(p, {"lat": s[6], "lon": s[5]})),
        "latitude": s[6],
        "longitude": s[5],
        **stamp,
    }
