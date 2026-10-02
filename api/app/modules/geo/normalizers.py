"""Transformation des réponses brutes en lignes de la base (fonctions pures, testables)."""

import re

from ...geo_utils import distance_to_geometry_meters, geojson_to_wkt, point_in_geometry, point_wkt
from ...parse import int_, iso_date, num, str_


def normalize_ban_feature(f: dict, stamp: dict) -> dict:
    lon, lat = f["geometry"]["coordinates"][:2]
    p = f["properties"]
    return {
        "banId": p["id"],
        "label": p["label"],
        "housenumber": str_(p.get("housenumber"), 16),
        "street": str_(p.get("street") or (p.get("name") if p.get("type") == "street" else None), 160),
        "postcode": str_(p.get("postcode"), 5),
        "city": str_(p.get("city"), 120),
        "inseeCode": p["citycode"],
        "latitude": lat,
        "longitude": lon,
        "location": point_wkt(lon, lat),
        "geocodeScore": num(p.get("score")),
        "geocodeType": p.get("type"),
        **stamp,
    }


def normalize_commune(c: dict, stamp: dict) -> dict:
    lon, lat = (c.get("centre") or {}).get("coordinates") or [0, 0]
    return {
        "inseeCode": c["code"],
        "name": c["nom"],
        "departmentCode": c["codeDepartement"],
        "departmentName": (c.get("departement") or {}).get("nom"),
        "regionCode": c.get("codeRegion"),
        "regionName": (c.get("region") or {}).get("nom"),
        "epciCode": c.get("codeEpci"),
        "postalCodes": c.get("codesPostaux") or [],
        "population": int_(c.get("population")),
        "surfaceHa": num(c.get("surface")),
        "latitude": lat,
        "longitude": lon,
        "center": point_wkt(lon, lat),
        **stamp,
    }


def normalize_parcel(f: dict, stamp: dict) -> dict:
    p = f["properties"]
    return {
        "idu": p["idu"],
        "inseeCode": p.get("code_insee") or f"{p.get('code_dep')}{p.get('code_com')}",
        "prefix": p.get("com_abs") or "000",
        "section": p["section"],
        "numero": p["numero"],
        "sheet": int_(p.get("feuille")),
        "areaM2": int_(p.get("contenance")),
        "geom": geojson_to_wkt(f["geometry"]),
        **stamp,
    }


def pick_parcel(features: list[dict], p: dict) -> dict | None:
    """Parcelle contenant le point, à défaut la plus proche."""
    if not features:
        return None
    containing = next((f for f in features if point_in_geometry(p, f["geometry"])), None)
    return containing or min(features, key=lambda f: distance_to_geometry_meters(p, f["geometry"]))


def _insee_from_partition(partition: str | None, fallback: str | None) -> str | None:
    """« DU_80021 » -> « 80021 » (les PLUi ont un SIREN d'EPCI : on garde alors la commune de l'adresse)."""
    m = re.match(r"^DU_(\d{5}|2[AB]\d{3})$", partition or "")
    return m[1] if m else fallback


def _yyyymmdd(v) -> str | None:
    s = str_(v)
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if s and re.fullmatch(r"\d{8}", s) else iso_date(s)


def normalize_plu_zone(f: dict, fallback_insee: str | None, stamp: dict) -> dict:
    p = f["properties"]
    return {
        "gpuId": str(f.get("id") or f"zone_urba.{p.get('gid')}"),
        "inseeCode": _insee_from_partition(p.get("partition"), fallback_insee),
        "documentId": str_(p.get("idurba"), 64),
        "label": str_(p.get("libelle"), 64),
        "labelLong": str_(p.get("libelong"), 255),
        "zoneType": str_(p.get("typezone"), 8),
        "approvedAt": _yyyymmdd(p.get("datappro") or p.get("datvalid")),
        "regulationFile": str_(p.get("urlfic") or p.get("nomfic"), 255),
        "geom": geojson_to_wkt(f["geometry"]),
        **stamp,
    }


PRESCRIPTION_KINDS = {"prescription-surf": "surface", "prescription-lin": "line", "prescription-pct": "point"}


def normalize_prescription(f: dict, layer: str, fallback_insee: str | None, stamp: dict) -> dict:
    p = f["properties"]
    return {
        "gpuId": str(f.get("id") or f"{layer}.{p.get('gid')}"),
        "inseeCode": _insee_from_partition(p.get("partition"), fallback_insee),
        "documentId": str_(p.get("idurba"), 64),
        "geometryKind": PRESCRIPTION_KINDS[layer],
        "typeCode": str_(p.get("typepsc"), 4),
        "subtypeCode": str_(p.get("stypepsc"), 4),
        "label": str_(p.get("libelle"), 255),
        "nature": str_(p.get("nature") if p.get("nature") is not None else p.get("txt"), 255),
        "geom": geojson_to_wkt(f["geometry"]),
        **stamp,
    }


def fix_mojibake(s: str | None) -> str | None:
    """Certains libellés GPU arrivent doublement encodés (UTF-8 lu en Latin-1)."""
    if not s or not re.search("[ÃÂ]", s):
        return s
    try:
        return s.encode("latin-1").decode("utf-8")
    except UnicodeError:
        return s


def normalize_easement(f: dict, stamp: dict) -> dict:
    p = f["properties"]
    name = p.get("nomsuplitt") if p.get("nomsuplitt") is not None else p.get("nomass")
    return {
        "gpuId": str(f.get("id") or f"assiette_sup_s.{p.get('gid')}"),
        "supType": str(p.get("suptype") or "").lower()[:8],
        "name": fix_mojibake(str_(name, 255)),
        "assietteType": str_(p.get("typeass"), 120),
        "generatorId": str_(p.get("idgen"), 120),
        "geom": geojson_to_wkt(f["geometry"]),
        **stamp,
    }


def normalize_monument(r: dict, stamp: dict) -> dict | None:
    if not r.get("Reference"):
        return None
    coords = [num(x) for x in str(r.get("coordonnees_au_format_WGS84") or "").split(",")]
    lat = coords[0] if coords else None
    lon = coords[1] if len(coords) > 1 else None
    return {
        "reference": r["Reference"],
        "name": str_(r.get("Titre_editorial_de_la_notice") or r.get("Denomination_de_l_edifice"), 255),
        "inseeCode": r.get("COG_Insee_lors_de_la_protection"),
        "denomination": str_(r.get("Denomination_de_l_edifice"), 255),
        "protectionType": str_(r.get("Typologie_de_la_protection"), 120),
        "protectionText": str_(r.get("Precision_de_la_protection") or r.get("Date_et_typologie_de_la_protection"), 1000),
        "latitude": lat,
        "longitude": lon,
        **stamp,
    }
