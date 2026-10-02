"""Annonces immobilières remontées par le service de scraping, stockées dans MongoDB (collection listings)."""

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ASCENDING, DESCENDING, UpdateOne

from ...errors import NotFound
from ...mongo import mongo
from ...parse import js_round, utcnow
from .normalizers import dedupe_by_source_id, normalize_listing
from .schemas import IngestListing, ListingFilter

SORTS = {
    "recent": [("lastSeenAt", DESCENDING), ("_id", DESCENDING)],
    "price": [("priceEur", ASCENDING), ("_id", ASCENDING)],
    "-price": [("priceEur", DESCENDING), ("_id", ASCENDING)],
    "priceM2": [("priceM2", ASCENDING), ("_id", ASCENDING)],
    "-priceM2": [("priceM2", DESCENDING), ("_id", ASCENDING)],
}


def _range(minimum=None, maximum=None) -> dict | None:
    bounds = {op: v for op, v in (("$gte", minimum), ("$lte", maximum)) if v is not None}
    return bounds or None


def build_filter(q: ListingFilter) -> dict:
    criteria = {
        "source": q.source,
        "transactionType": q.transactionType,
        "propertyType": q.propertyType,
        "inseeCode": getattr(q, "insee", None),
        "postalCode": getattr(q, "postalCode", None),
        "departmentCode": getattr(q, "department", None),
        "priceEur": _range(q.minPrice, q.maxPrice),
        "areaM2": _range(q.minArea, q.maxArea),
        "rooms": _range(q.minRooms),
    }
    return {k: v for k, v in criteria.items() if v is not None}


async def ingest(source: str, items: list[IngestListing]) -> dict:
    """Upsert idempotent d'un lot : une annonce déjà connue est mise à jour, un changement de prix est historisé."""
    now = utcnow()
    rows = dedupe_by_source_id([normalize_listing(source, i) for i in items])
    known = mongo.listings.find(
        {"source": source, "sourceId": {"$in": [r["sourceId"] for r in rows]}}, {"sourceId": 1, "priceEur": 1}
    )
    previous_price = {k["sourceId"]: k["priceEur"] async for k in known}

    price_changes = 0
    ops = []
    for row in rows:
        known_listing = row["sourceId"] in previous_price
        price_changed = previous_price.get(row["sourceId"]) != row["priceEur"]
        if price_changed and known_listing:
            price_changes += 1
        update = {
            "$set": {**row, "lastSeenAt": now, "updatedAt": now},
            "$setOnInsert": {"firstSeenAt": now, "createdAt": now} | ({} if "photos" in row else {"photos": []}),
        }
        if price_changed:
            update["$push"] = {"priceHistory": {"priceEur": row["priceEur"], "at": now}}
        ops.append(UpdateOne({"source": source, "sourceId": row["sourceId"]}, update, upsert=True))
    res = await mongo.listings.bulk_write(ops, ordered=False)

    return {
        "source": source,
        "received": len(items),
        "created": res.upserted_count,
        "updated": len(rows) - res.upserted_count,
        "priceChanges": price_changes,
        "ingestedAt": now,
    }


async def search(q) -> dict:
    criteria = build_filter(q)
    cursor = mongo.listings.find(criteria, {"raw": 0}).sort(SORTS[q.sort]).skip(q.offset).limit(q.limit)
    return {
        "total": await mongo.listings.count_documents(criteria),
        "page": q.page,
        "limit": q.limit,
        "items": await cursor.to_list(),
    }


async def get(listing_id: str) -> dict:
    try:
        listing = await mongo.listings.find_one({"_id": ObjectId(listing_id)})
    except InvalidId:
        listing = None
    if not listing:
        raise NotFound(f"Annonce {listing_id} inconnue")
    return listing


async def near(p: dict, q) -> dict:
    """Annonces géolocalisées autour d'un point, de la plus proche à la plus lointaine."""
    cursor = await mongo.listings.aggregate([
        {
            "$geoNear": {
                "near": {"type": "Point", "coordinates": [p["lon"], p["lat"]]},
                "distanceField": "distanceM",
                "maxDistance": q.radius,
                "spherical": True,
                "query": build_filter(q),
            }
        },
        {"$skip": q.offset},
        {"$limit": q.limit},
        {"$project": {"raw": 0}},
        {"$set": {"distanceM": {"$round": ["$distanceM", 0]}}},
    ])
    return {"radius": q.radius, "page": q.page, "limit": q.limit, "items": await cursor.to_list()}


async def commune_stats(insee: str) -> dict:
    """Prix au m² des annonces d'une commune, par type de transaction et de bien."""
    cursor = await mongo.listings.aggregate([
        {"$match": {"inseeCode": insee, "priceM2": {"$gt": 0}}},
        {
            "$group": {
                "_id": {"transactionType": "$transactionType", "propertyType": "$propertyType"},
                "listingsCount": {"$sum": 1},
                "medianPriceM2": {"$median": {"input": "$priceM2", "method": "approximate"}},
                "avgPriceM2": {"$avg": "$priceM2"},
                "minPriceM2": {"$min": "$priceM2"},
                "maxPriceM2": {"$max": "$priceM2"},
                "lastSeenAt": {"$max": "$lastSeenAt"},
            }
        },
        {"$sort": {"_id.transactionType": 1, "_id.propertyType": 1}},
    ])
    groups = [
        {
            **g.pop("_id"),
            **g,
            "medianPriceM2": js_round(g["medianPriceM2"] * 100) / 100,
            "avgPriceM2": js_round(g["avgPriceM2"] * 100) / 100,
        }
        async for g in cursor
    ]
    return {"inseeCode": insee, "total": await mongo.listings.count_documents({"inseeCode": insee}), "groups": groups}
