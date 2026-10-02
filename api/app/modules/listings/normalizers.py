import re

from ...parse import js_round, parse_datetime
from .schemas import IngestListing


def department_of(insee_code: str | None = None, postal_code: str | None = None) -> str | None:
    """« 80021 » -> « 80 », « 97411 » -> « 974 », « 2A004 » -> « 2A ». Repli sur le code postal (Corse : 20xxx, non déterminable)."""
    code = insee_code or (postal_code if postal_code and not postal_code.startswith("20") else None)
    if not code:
        return None
    return code[:3] if code.startswith(("97", "98")) else code[:2]


def price_m2(price_eur: float, area_m2: float | None, rent: bool) -> float | None:
    """Prix au m², arrondi à l'euro (au centime pour un loyer). Indéfini sans surface exploitable."""
    if not area_m2 or area_m2 <= 0 or price_eur <= 0:
        return None
    v = price_eur / area_m2
    return js_round(v * 100) / 100 if rent else js_round(v)


def _text(v: str | None) -> str | None:
    return re.sub(r"\s+", " ", v).strip() or None if v else None


def _number(v: float | None) -> float | int | None:
    return int(v) if isinstance(v, float) and v.is_integer() else v


def normalize_listing(source: str, item: IngestListing) -> dict:
    """Annonce validée -> document MongoDB, sans les clés absentes (une réingestion partielle n'efface rien)."""
    has_point = item.lat is not None and item.lon is not None
    doc = {
        "source": source,
        "sourceId": item.sourceId.strip(),
        "url": str(item.url),
        "transactionType": item.transactionType,
        "propertyType": item.propertyType,
        "title": _text(item.title),
        "description": (item.description or "").strip() or None,
        "priceEur": _number(item.priceEur),
        "areaM2": _number(item.areaM2),
        "landAreaM2": _number(item.landAreaM2),
        "priceM2": price_m2(item.priceEur, item.areaM2, item.transactionType == "rent"),
        "rooms": item.rooms,
        "bedrooms": item.bedrooms,
        "floor": item.floor,
        "energyClass": item.energyClass.upper() if item.energyClass else None,
        "ghgClass": item.ghgClass.upper() if item.ghgClass else None,
        "city": _text(item.city),
        "postalCode": item.postalCode,
        "inseeCode": item.inseeCode,
        "departmentCode": department_of(item.inseeCode, item.postalCode),
        "location": {"type": "Point", "coordinates": [item.lon, item.lat]} if has_point else None,
        "photos": list(dict.fromkeys(str(p) for p in item.photos)) if item.photos else None,
        "publishedAt": parse_datetime(item.publishedAt),
        "raw": item.raw,
    }
    return {k: v for k, v in doc.items() if v is not None}


def dedupe_by_source_id(items: list[dict]) -> list[dict]:
    """Dernière occurrence de chaque sourceId (un lot peut contenir la même annonce sur deux pages)."""
    return list({i["sourceId"]: i for i in items}.values())
