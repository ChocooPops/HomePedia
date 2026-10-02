"""Calculs géométriques. Un point est un dict { "lat": ..., "lon": ... } ; les géométries sont du GeoJSON."""

import math

from .parse import round_to

EARTH_RADIUS_M = 6371008.8


def point_wkt(lon: float, lat: float) -> str:
    """WKT d'un point, ordre « lon lat » (convention MariaDB / GeoJSON)."""
    return f"POINT({_n(round_to(lon, 7))} {_n(round_to(lat, 7))})"


def _n(v: float) -> str:
    return repr(int(v)) if float(v).is_integer() else repr(float(v))


def _coords(points) -> str:
    return ",".join(f"{_n(p[0])} {_n(p[1])}" for p in points)


def _rings(rings) -> str:
    return ",".join(f"({_coords(r)})" for r in rings)


def geojson_to_wkt(geometry: dict) -> str:
    """GeoJSON (Point, LineString, Polygon, Multi*, GeometryCollection) -> WKT. Ignore le CRS embarqué et l'altitude."""
    t, c = geometry["type"], geometry.get("coordinates")
    if t == "Point":
        return f"POINT({_n(c[0])} {_n(c[1])})"
    if t == "LineString":
        return f"LINESTRING({_coords(c)})"
    if t == "Polygon":
        return f"POLYGON({_rings(c)})"
    if t == "MultiPoint":
        return f"MULTIPOINT({_coords(c)})"
    if t == "MultiLineString":
        return f"MULTILINESTRING({_rings(c)})"
    if t == "MultiPolygon":
        return "MULTIPOLYGON(" + ",".join(f"({_rings(p)})" for p in c) + ")"
    if t == "GeometryCollection":
        return "GEOMETRYCOLLECTION(" + ",".join(geojson_to_wkt(g) for g in geometry["geometries"]) + ")"
    raise ValueError(f"Géométrie GeoJSON non gérée : {t}")


def haversine_meters(a: dict, b: dict) -> float:
    d_lat = math.radians(b["lat"] - a["lat"])
    d_lon = math.radians(b["lon"] - a["lon"])
    h = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(a["lat"])) * math.cos(math.radians(b["lat"])) * math.sin(d_lon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def bbox_around(center: dict, radius_m: float) -> dict:
    d_lat = math.degrees(radius_m / EARTH_RADIUS_M)
    d_lon = d_lat / math.cos(math.radians(center["lat"]))
    return {
        "minLat": center["lat"] - d_lat, "maxLat": center["lat"] + d_lat,
        "minLon": center["lon"] - d_lon, "maxLon": center["lon"] + d_lon,
    }


def bbox_polygon_wkt(b: dict) -> str:
    return (
        f"POLYGON(({b['minLon']!r} {b['minLat']!r},{b['maxLon']!r} {b['minLat']!r},{b['maxLon']!r} {b['maxLat']!r},"
        f"{b['minLon']!r} {b['maxLat']!r},{b['minLon']!r} {b['minLat']!r}))"
    )


def square_geojson(center: dict, half_side_m: float) -> dict:
    """Carré GeoJSON centré sur un point (sert aux API qui n'acceptent pas les points)."""
    b = bbox_around(center, half_side_m)
    return {
        "type": "Polygon",
        "coordinates": [[
            [b["minLon"], b["minLat"]], [b["maxLon"], b["minLat"]], [b["maxLon"], b["maxLat"]],
            [b["minLon"], b["maxLat"]], [b["minLon"], b["minLat"]],
        ]],
    }


def _ring_contains(ring, p: dict) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > p["lat"]) != (yj > p["lat"]) and p["lon"] < (xj - xi) * (p["lat"] - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def point_in_geometry(p: dict, geometry: dict | None) -> bool:
    """Test point dans (Multi)Polygon GeoJSON, par lancer de rayon."""
    if not geometry:
        return False
    if geometry["type"] == "Polygon":
        polygons = [geometry["coordinates"]]
    elif geometry["type"] == "MultiPolygon":
        polygons = geometry["coordinates"]
    else:
        polygons = []
    return any(
        rings and _ring_contains(rings[0], p) and not any(_ring_contains(hole, p) for hole in rings[1:])
        for rings in polygons
    )


def distance_to_geometry_meters(p: dict, geometry: dict | None) -> float:
    """
    Distance minimale (m) entre un point et une géométrie GeoJSON.
    Projection équirectangulaire locale : précision métrique suffisante sous ~50 km.
    """
    if not geometry:
        return math.inf
    t, c = geometry["type"], geometry.get("coordinates")
    if t == "Point":
        return haversine_meters(p, {"lon": c[0], "lat": c[1]})
    if t in ("Polygon", "MultiPolygon") and point_in_geometry(p, geometry):
        return 0
    if t == "LineString":
        lines = [c]
    elif t in ("MultiLineString", "Polygon"):
        lines = c
    elif t == "MultiPolygon":
        lines = [ring for polygon in c for ring in polygon]
    else:
        lines = []
    kx = math.cos(math.radians(p["lat"])) * 111320
    ky = 110540
    best = math.inf
    for line in lines:
        for i in range(len(line) - 1):
            ax, ay = (line[i][0] - p["lon"]) * kx, (line[i][1] - p["lat"]) * ky
            bx, by = (line[i + 1][0] - p["lon"]) * kx, (line[i + 1][1] - p["lat"]) * ky
            dx, dy = bx - ax, by - ay
            len2 = dx * dx + dy * dy
            t_ = 0 if len2 == 0 else max(0, min(1, -(ax * dx + ay * dy) / len2))
            best = min(best, math.hypot(ax + t_ * dx, ay + t_ * dy))
    return best
