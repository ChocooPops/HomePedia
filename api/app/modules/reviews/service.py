"""
Avis (données textuelles, MongoDB collection reviews) :
 - Google Maps Places API : avis des lieux autour d'une adresse (clé payante, 5 avis au plus par lieu) ;
 - MeilleursAgents : avis de quartiers et d'agences, importés depuis des fichiers exportés à la main.
"""

import hashlib
import re

from pymongo import DESCENDING, UpdateOne

from ...collector import collector
from ...config import settings
from ...errors import MissingApiKeyError
from ...http_client import http
from ...mongo import mongo
from ...parse import iso_date, js_round, parse_datetime, utcnow
from ..geo.service import point_of

PLACES_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"
PLACES_FIELDS = ",".join(
    f"places.{f}"
    for f in ("id", "displayName", "formattedAddress", "location", "rating", "userRatingCount", "primaryType", "googleMapsUri", "reviews")
)


# ---------------------------------------------------------------- Google


async def places_nearby(p: dict, radius_m: int) -> list[dict]:
    key = settings.google_maps_api_key
    if not key:
        raise MissingApiKeyError("google_places", "GOOGLE_MAPS_API_KEY")
    res = await http.post(
        PLACES_NEARBY_URL,
        {
            "maxResultCount": 20,
            "languageCode": "fr",
            "locationRestriction": {"circle": {"center": {"latitude": p["lat"], "longitude": p["lon"]}, "radius": radius_m}},
        },
        source="google_places",
        headers={"X-Goog-Api-Key": key, "X-Goog-FieldMask": PLACES_FIELDS},
    )
    return res.get("places") or []


def normalize_place_reviews(place: dict, address: dict) -> list[dict]:
    """Un document par avis ; la note globale du lieu est recopiée sur chacun."""
    location = place.get("location") or {}
    subject = {
        "source": "google_places",
        "kind": "place",
        "subjectId": place.get("id"),
        "subjectName": (place.get("displayName") or {}).get("text"),
        "subjectType": place.get("primaryType"),
        "subjectRating": place.get("rating"),
        "subjectRatingCount": place.get("userRatingCount"),
        "subjectAddress": place.get("formattedAddress"),
        "url": place.get("googleMapsUri"),
        "inseeCode": address["inseeCode"],
        "city": address.get("city"),
        "postalCode": address.get("postcode"),
    }
    if "latitude" in location and "longitude" in location:
        subject["location"] = {"type": "Point", "coordinates": [location["longitude"], location["latitude"]]}
    return [
        {
            **subject,
            "externalId": r.get("name") or f"{place.get('id')}:{i}",
            "rating": r.get("rating"),
            "text": ((r.get("originalText") or r.get("text") or {}).get("text") or "").strip() or None,
            "language": (r.get("originalText") or r.get("text") or {}).get("languageCode"),
            "author": (r.get("authorAttribution") or {}).get("displayName"),
            "publishedAt": parse_datetime(r.get("publishTime")),
        }
        for i, r in enumerate(place.get("reviews") or [])
    ]


async def collect_google(address: dict, radius_m: int = 500, force: bool = False) -> dict:
    async def task(_stamp: dict) -> dict:
        places = await places_nearby(point_of(address), radius_m)
        docs = [d for place in places for d in normalize_place_reviews(place, address)]
        await _save(docs)
        return {"items": len(docs)}

    return await collector.run("google_places", f"address:{address['id']}:r{radius_m}", task, force=force)


# ---------------------------------------------------------------- Import


def _external_id(kind: str, item: dict) -> str:
    key = "|".join(str(item.get(k) or "") for k in ("subject", "author", "date", "text"))
    return hashlib.sha1(f"{kind}|{key}".encode()).hexdigest()


def normalize_imported_review(source: str, kind: str, item: dict) -> dict:
    """Ligne d'un fichier exporté -> document d'avis, sans les clés absentes."""
    date = item.get("date")
    doc = {
        "source": source,
        "kind": kind,
        "externalId": item.get("externalId") or _external_id(kind, item),
        "subjectName": re.sub(r"\s+", " ", item["subject"]).strip(),
        "rating": item.get("rating"),
        "text": (item.get("text") or "").strip() or None,
        "author": (item.get("author") or "").strip() or None,
        "publishedAt": parse_datetime(iso_date(date)) if date else None,
        "url": item.get("url"),
        "inseeCode": item.get("inseeCode"),
        "city": (item.get("city") or "").strip() or None,
        "postalCode": item.get("postalCode"),
    }
    return {k: v for k, v in doc.items() if v is not None}


async def import_reviews(source: str, kind: str, items: list[dict]) -> dict:
    docs = list({d["externalId"]: d for d in (normalize_imported_review(source, kind, i) for i in items)}.values())
    created = await _save(docs)
    return {"source": source, "kind": kind, "received": len(items), "created": created, "updated": len(docs) - created, "importedAt": utcnow()}


async def _save(docs: list[dict]) -> int:
    """Upsert sur (source, externalId) ; renvoie le nombre de nouveaux avis."""
    if not docs:
        return 0
    now = utcnow()
    res = await mongo.reviews.bulk_write(
        [
            UpdateOne(
                {"source": d["source"], "externalId": d["externalId"]},
                {"$set": {**d, "updatedAt": now}, "$setOnInsert": {"importedAt": now}},
                upsert=True,
            )
            for d in docs
        ],
        ordered=False,
    )
    return res.upserted_count


# --------------------------------------------------------------- Lecture


async def search(q) -> dict:
    criteria = {
        "source": q.source,
        "kind": q.kind,
        "inseeCode": q.insee,
        "postalCode": q.postalCode,
        "rating": {"$gte": q.minRating} if q.minRating is not None else None,
        "text": {"$regex": re.escape(q.q), "$options": "i"} if q.q else None,
    }
    criteria = {k: v for k, v in criteria.items() if v is not None}
    cursor = mongo.reviews.find(criteria).sort([("publishedAt", DESCENDING), ("_id", DESCENDING)]).skip(q.offset).limit(q.limit)
    return {"total": await mongo.reviews.count_documents(criteria), "page": q.page, "limit": q.limit, "items": await cursor.to_list()}


async def summary(insee: str) -> dict:
    """Nombre d'avis et note moyenne de la commune, par source et par type."""
    cursor = await mongo.reviews.aggregate([
        {"$match": {"inseeCode": insee}},
        {
            "$group": {
                "_id": {"source": "$source", "kind": "$kind"},
                "reviewsCount": {"$sum": 1},
                "avgRating": {"$avg": "$rating"},
                "subjects": {"$addToSet": "$subjectName"},
            }
        },
        {"$sort": {"_id.source": 1, "_id.kind": 1}},
    ])
    groups = [
        {
            **g["_id"],
            "reviewsCount": g["reviewsCount"],
            "avgRating": js_round(g["avgRating"] * 100) / 100 if g["avgRating"] is not None else None,
            "subjectsCount": len(g["subjects"]),
        }
        async for g in cursor
    ]
    return {"inseeCode": insee, "total": sum(g["reviewsCount"] for g in groups), "groups": groups}
