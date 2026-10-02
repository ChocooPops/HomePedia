"""Transformation des réponses brutes en lignes de la base (fonctions pures, testables)."""

from ...geo_utils import point_wkt
from ...parse import bool_from_flag, int_, num, parse_datetime, str_

CONNECTOR_FLAGS = ("prise_type_ef", "prise_type_2", "prise_type_combo_ccs", "prise_type_chademo", "prise_type_autre")


def _nullish(a, b):
    """`a ?? b` : ne retombe sur b que si a est absent ou nul."""
    return a if a is not None else b


def stop_mode(t: dict) -> str | None:
    if t.get("railway") in ("station", "halt"):
        return "metro" if t.get("station") == "subway" else "train"
    if t.get("railway") == "tram_stop":
        return "tram"
    if t.get("highway") == "bus_stop" or t.get("amenity") == "bus_station":
        return "bus"
    return None


def normalize_charger(r: dict, insee: str, stamp: dict) -> dict | None:
    lon = num(r.get("consolidated_longitude"))
    lat = num(r.get("consolidated_latitude"))
    if not r.get("id_pdc_itinerance") or lat is None or lon is None:
        return None
    return {
        "pdcId": str(r["id_pdc_itinerance"])[:64],
        "stationName": str_(r.get("nom_station"), 255),
        "operatorName": str_(_nullish(r.get("nom_operateur"), r.get("nom_amenageur")), 160),
        "inseeCode": insee,
        "powerKw": num(r.get("puissance_nominale")),
        "connectors": [k.replace("prise_type_", "", 1) for k in CONNECTOR_FLAGS if bool_from_flag(r.get(k))],
        "isFree": bool_from_flag(r.get("gratuit")),
        "accessCondition": str_(r.get("condition_acces"), 80),
        "openingHours": str_(r.get("horaires"), 255),
        "latitude": lat,
        "longitude": lon,
        "location": point_wkt(lon, lat),
        **stamp,
    }


def normalize_parking(r: dict, insee: str, stamp: dict) -> dict | None:
    lat = num(r.get("Ylat"))
    lon = num(r.get("Xlong"))
    if not r.get("id") or lat is None or lon is None:
        return None
    return {
        "externalId": str(r["id"])[:64],
        "name": str_(r.get("nom"), 255),
        "inseeCode": insee,
        "places": int_(r.get("nb_places")),
        "pmrPlaces": int_(r.get("nb_pmr")),
        "evPlaces": int_(r.get("nb_voitures_electriques")),
        "isFree": bool_from_flag(r.get("gratuit")),
        "hourlyRateEur": num(r.get("tarif_1h")),
        "residentSubscriptionEur": num(r.get("abo_resident")),
        "latitude": lat,
        "longitude": lon,
        "location": point_wkt(lon, lat),
        **stamp,
    }


def normalize_stop(e: dict, stamp: dict) -> dict | None:
    t = e.get("tags") or {}
    mode = stop_mode(t)
    center = e.get("center") or {}
    lat = _nullish(e.get("lat"), center.get("lat"))
    lon = _nullish(e.get("lon"), center.get("lon"))
    if not mode or lat is None or lon is None:
        return None
    return {
        "externalId": f"osm:{e['type']}/{e['id']}",
        "name": str_(t.get("name"), 255),
        "mode": mode,
        "network": str_(_nullish(t.get("network"), t.get("operator")), 160),
        "latitude": lat,
        "longitude": lon,
        "location": point_wkt(lon, lat),
        **stamp,
    }


def coverage_level(areas: list[dict], c: dict) -> str | None:
    """Le jeu couvre-t-il la commune (directement, via son EPCI, son département ou sa région) ?"""
    for a in areas:
        kind, insee = a.get("type"), a.get("insee")
        if kind == "commune" and insee == c["inseeCode"]:
            return "commune"
        if kind == "epci" and insee == c["epciCode"]:
            return "epci"
        if kind == "departement" and insee == c["departmentCode"]:
            return "departement"
        if kind == "region" and insee == c["regionCode"]:
            return "region"
    return None


def normalize_feed(d: dict, level: str, insee: str, stamp: dict) -> dict:
    resources = d.get("resources") or []
    gtfs = next((r for r in resources if r.get("format") == "GTFS" and r.get("type") == "main"), None)
    if gtfs is None:
        gtfs = next((r for r in resources if r.get("format") == "GTFS"), None)
    gtfs = gtfs or {}
    return {
        "datasetId": str(d["id"]),
        "inseeCode": insee,
        "title": str(d.get("title"))[:255],
        "publisher": str_((d.get("publisher") or {}).get("name"), 160),
        "gtfsUrl": str_(gtfs.get("url"), 500),
        "isAvailable": gtfs.get("is_available"),
        "coverageLevel": level,
        "updatedAt": parse_datetime(gtfs["updated"]) if gtfs.get("updated") else None,
        **stamp,
    }
