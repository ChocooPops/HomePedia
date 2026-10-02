"""Normalisation des lieux de service (OSM, Recherche d'entreprises). Fonctions pures."""

import re

from ...geo_utils import point_wkt
from ...parse import num, str_
from .clients import NAF_CATEGORIES


def osm_category(t: dict) -> str | None:
    if t.get("emergency") == "yes" and (t.get("amenity") == "hospital" or t.get("healthcare") == "hospital"):
        return "emergency"
    if t.get("amenity") == "pharmacy":
        return "pharmacy"
    if t.get("amenity") in ("childcare", "kindergarten"):
        return "childcare"
    if t.get("shop") == "bakery":
        return "bakery"
    return None


def opens_on_sunday(hours: str | None) -> bool | None:
    """Heuristique : horaires OSM mentionnant le dimanche (« Su ») hors « Su off »."""
    if not hours:
        return None
    if re.search(r"Su\s*(off|closed)", hours, flags=re.IGNORECASE):
        return False
    return re.search(r"\bSu\b|Mo-Su|24/7", hours) is not None


def normalize_osm_service(e: dict, stamp: dict) -> dict | None:
    t = e.get("tags") or {}
    category = osm_category(t)
    center = e.get("center") or {}
    lat = e["lat"] if e.get("lat") is not None else center.get("lat")
    lon = e["lon"] if e.get("lon") is not None else center.get("lon")
    if not category or lat is None or lon is None:
        return None
    return {
        "externalId": f"osm:{e['type']}/{e['id']}",
        "category": category,
        "name": str_(t.get("name"), 255),
        "addressLabel": str_(" ".join(v for v in (t.get("addr:housenumber"), t.get("addr:street"), t.get("addr:city")) if v), 255),
        "openingHours": str_(t.get("opening_hours"), 255),
        "details": {"opensOnSunday": opens_on_sunday(t.get("opening_hours")), "operator": t.get("operator")},
        "latitude": lat,
        "longitude": lon,
        "location": point_wkt(lon, lat),
        **stamp,
    }


def normalize_establishment(e: dict, stamp: dict) -> dict | None:
    lat = num(e.get("latitude"))
    lon = num(e.get("longitude"))
    category = NAF_CATEGORIES.get(e.get("activite_principale"))
    if e.get("etat_administratif") != "A" or lat is None or lon is None or not category:
        return None
    name = e.get("nom_commercial")
    if name is None:
        name = next(iter(e.get("liste_enseignes") or []), None)
    if name is None:
        name = e.get("nom_complet")
    # Une propriété absente de la réponse n'est pas écrite (pas de null).
    details = {
        key: e[field]
        for key, field in (("siret", "siret"), ("naf", "activite_principale"), ("createdAt", "date_creation"))
        if field in e
    }
    return {
        "externalId": f"siret:{e.get('siret')}",
        "category": category,
        "name": str_(name, 255),
        "addressLabel": str_(e.get("adresse"), 255),
        "inseeCode": str_(e.get("commune"), 5),
        "details": details,
        "latitude": lat,
        "longitude": lon,
        "location": point_wkt(lon, lat),
        **stamp,
    }
