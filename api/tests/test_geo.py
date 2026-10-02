from datetime import datetime

from app.modules.geo.normalizers import fix_mojibake, normalize_ban_feature, normalize_monument, pick_parcel

STAMP = {"sourceCode": "test", "fetchedAt": datetime(2026, 1, 1), "expiresAt": datetime(2026, 2, 1)}


def test_repare_les_libelles_gpu_doublement_encodes():
    assert fix_mojibake("PÃ©rimÃ¨tre dÃ©limitÃ©") == "Périmètre délimité"
    assert fix_mojibake("Déjà correct") == "Déjà correct"


def test_lit_les_coordonnees_lat_lon_des_monuments_historiques():
    m = normalize_monument(
        {"Reference": "PA1", "COG_Insee_lors_de_la_protection": "80021", "coordonnees_au_format_WGS84": "49.89,2.30"}, STAMP
    )
    assert (m["reference"], m["latitude"], m["longitude"]) == ("PA1", 49.89, 2.3)
    assert normalize_monument({}, STAMP) is None


def test_normalise_une_adresse_ban():
    feature = {
        "geometry": {"type": "Point", "coordinates": [2.297087, 49.892808]},
        "properties": {
            "id": "80021_6820_00002", "label": "2 Rue de la République 80000 Amiens", "score": 0.8004,
            "housenumber": "2", "street": "Rue de la République", "postcode": "80000", "city": "Amiens",
            "citycode": "80021", "type": "housenumber",
        },
    }
    row = normalize_ban_feature(feature, STAMP)
    assert row["banId"] == "80021_6820_00002"
    assert row["location"] == "POINT(2.297087 49.892808)"
    assert row["inseeCode"] == "80021"
    assert row["sourceCode"] == "test"


def test_choisit_la_parcelle_contenant_le_point_sinon_la_plus_proche():
    def square(x):
        return {"geometry": {"type": "Polygon", "coordinates": [[[x, 0], [x + 1, 0], [x + 1, 1], [x, 1], [x, 0]]]}, "x": x}

    features = [square(0), square(2), square(5)]
    assert pick_parcel(features, {"lon": 2.5, "lat": 0.5})["x"] == 2
    assert pick_parcel(features, {"lon": 4.5, "lat": 0.5})["x"] == 5
    assert pick_parcel([], {"lon": 0, "lat": 0}) is None
