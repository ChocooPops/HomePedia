import pytest

from app.geo_utils import (
    bbox_around,
    distance_to_geometry_meters,
    geojson_to_wkt,
    haversine_meters,
    point_in_geometry,
    point_wkt,
)

AMIENS = {"lat": 49.892808, "lon": 2.297087}
SQUARE = {"type": "Polygon", "coordinates": [[[2.29, 49.89], [2.30, 49.89], [2.30, 49.90], [2.29, 49.90], [2.29, 49.89]]]}


def test_point_wkt_ordre_lon_lat():
    assert point_wkt(2.297087, 49.892808) == "POINT(2.297087 49.892808)"


def test_distance_haversine_amiens_paris():
    assert 110000 < haversine_meters(AMIENS, {"lat": 48.8566, "lon": 2.3522}) < 120000


def test_point_dans_polygone_trous_compris():
    assert point_in_geometry(AMIENS, SQUARE) is True
    assert point_in_geometry({"lat": 49.95, "lon": 2.297}, SQUARE) is False
    hole = [[2.296, 49.892], [2.298, 49.892], [2.298, 49.894], [2.296, 49.894], [2.296, 49.892]]
    assert point_in_geometry(AMIENS, {**SQUARE, "coordinates": [*SQUARE["coordinates"], hole]}) is False


def test_distance_point_ligne():
    line = {"type": "LineString", "coordinates": [[2.29, 49.9], [2.31, 49.9]]}
    assert 750 < distance_to_geometry_meters(AMIENS, line) < 850
    assert distance_to_geometry_meters(AMIENS, SQUARE) == 0


def test_boite_englobante_symetrique():
    b = bbox_around(AMIENS, 1000)
    assert haversine_meters(AMIENS, {"lat": b["maxLat"], "lon": AMIENS["lon"]}) == pytest.approx(1000, abs=5)
    assert haversine_meters(AMIENS, {"lat": AMIENS["lat"], "lon": b["maxLon"]}) == pytest.approx(1000, abs=5)


def test_geojson_vers_wkt():
    assert geojson_to_wkt({"type": "Point", "coordinates": [2.3, 49.9], "crs": {"type": "name"}}) == "POINT(2.3 49.9)"
    assert geojson_to_wkt({"type": "LineString", "coordinates": [[2, 49], [2.5, 49.5, 30]]}) == "LINESTRING(2 49,2.5 49.5)"
    multi = {"type": "MultiPolygon", "coordinates": [SQUARE["coordinates"], [[[0, 0], [1, 0], [1, 1], [0, 0]]]]}
    assert geojson_to_wkt(multi) == (
        "MULTIPOLYGON(((2.29 49.89,2.3 49.89,2.3 49.9,2.29 49.9,2.29 49.89)),((0 0,1 0,1 1,0 0)))"
    )
