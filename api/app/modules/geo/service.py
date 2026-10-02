"""Adresses (entité pivot), communes, parcelles et indicateurs d'adresse."""

from ...collector import collector
from ...db import db
from ...errors import BadRequest, NotFound, Unprocessable
from ...parse import chunk
from . import clients
from .normalizers import normalize_ban_feature, normalize_commune, normalize_parcel, pick_parcel

# Score BAN minimal pour accepter un géocodage sans ambiguïté.
MIN_GEOCODE_SCORE = 0.5


def point_of(address: dict) -> dict:
    return {"lat": address["latitude"], "lon": address["longitude"]}


# ------------------------------------------------------------------ BAN


async def search(q: str, limit: int = 5) -> list[dict]:
    """Autocomplétion / recherche sans persistance."""
    return [
        {
            "label": f["properties"]["label"],
            "score": f["properties"]["score"],
            "type": f["properties"]["type"],
            "banId": f["properties"]["id"],
            "inseeCode": f["properties"]["citycode"],
            "latitude": f["geometry"]["coordinates"][1],
            "longitude": f["geometry"]["coordinates"][0],
        }
        for f in await clients.ban_search(q, limit=limit)
    ]


async def geocode_and_save(q: str, force: bool = False) -> dict:
    """Géocode une adresse texte et l'enregistre (commune + parcelle rattachées)."""
    features = await clients.ban_search(q, limit=1)
    if not features:
        raise NotFound(f"Adresse introuvable : « {q} »")
    best = features[0]
    score = best["properties"]["score"]
    if score < MIN_GEOCODE_SCORE:
        raise Unprocessable(
            f"Géocodage peu fiable (score {score:.2f}) : précisez l'adresse", candidate=best["properties"]["label"]
        )
    return await _save_feature(best, force)


async def reverse_and_save(p: dict, force: bool = False) -> dict:
    """Géocodage inverse d'un point puis enregistrement."""
    features = await clients.ban_reverse(p)
    if not features:
        raise NotFound(f"Aucune adresse BAN à proximité de {p['lat']},{p['lon']}")
    return await _save_feature(features[0], force)


async def _save_feature(f: dict, force: bool) -> dict:
    commune = await ensure_commune(f["properties"]["citycode"], force)

    stamp = collector.stamp("ban")
    values = normalize_ban_feature(f, stamp)
    await db.upsert("address", values)
    address = await db.find_one("address", {"banId": values["banId"]})
    ban = {
        "source": "ban", "target": f"address:{address['id']}", "status": "success", "items": 1,
        "fetchedAt": stamp["fetchedAt"], "expiresAt": stamp["expiresAt"],
    }
    parcel = await collect_parcel(address, force)
    return {"address": await get_address(address["id"]), "outcomes": [ban, commune, parcel]}


# ------------------------------------------------------------- Communes


async def ensure_commune(insee: str, force: bool = False) -> dict:
    target = f"commune:{insee}"
    if not force and await db.exists("commune", {"inseeCode": insee}):
        fresh = await collector.fresh_log("geo_api", target)
        if fresh:
            return {
                "source": "geo_api", "target": target, "status": "cached", "items": 1,
                "fetchedAt": fresh["fetchedAt"], "expiresAt": fresh["expiresAt"],
            }

    async def task(stamp: dict) -> dict:
        raw = await clients.geo_api_commune(insee)
        if not raw:
            raise NotFound(f"Commune INSEE inconnue : {insee}")
        await db.upsert("commune", normalize_commune(raw, stamp))
        return {"items": 1, "raw": raw}

    outcome = await collector.run("geo_api", target, task, force=True)
    if outcome["status"] == "error" and not await db.exists("commune", {"inseeCode": insee}):
        raise BadRequest(f"Impossible de récupérer la commune {insee} : {outcome['error']}")
    return outcome


async def collect_department_communes(dep: str, force: bool = False) -> dict:
    """Importe toutes les communes d'un département (utile avant un import DVF ou SSMSI)."""

    async def task(stamp: dict) -> dict:
        raw = await clients.geo_api_communes_of_department(dep)
        rows = [normalize_commune(c, stamp) for c in raw if c.get("centre")]
        for c in chunk(rows, 200):
            await db.upsert("commune", c)
        return {"items": len(rows)}

    return await collector.run("geo_api", f"department:{dep}", task, force=force)


async def get_commune(insee: str) -> dict:
    commune = await db.find_one("commune", {"inseeCode": insee})
    if not commune:
        await ensure_commune(insee)
        commune = await db.find_one("commune", {"inseeCode": insee})
    return commune


async def list_communes(department: str | None, region: str | None, limit: int, offset: int) -> tuple[list[dict], int]:
    where = {k: v for k, v in {"departmentCode": department, "regionCode": region}.items() if v}
    items = await db.find("commune", where, order="t.insee_code ASC", limit=limit, offset=offset)
    return items, await db.count("commune", where)


# ------------------------------------------------------------- Parcelle


async def collect_parcel(address: dict, force: bool = False) -> dict:
    async def task(stamp: dict) -> dict:
        p = point_of(address)
        features = await clients.cadastre_parcels_around(p)
        chosen = pick_parcel(features, p)
        if not chosen:
            return {"items": 0, "raw": features}
        parcel = normalize_parcel(chosen, stamp)
        if parcel["inseeCode"] != address["inseeCode"]:
            await ensure_commune(parcel["inseeCode"])
        await db.upsert("parcel", parcel)
        await db.update("address", {"id": address["id"]}, {"parcelIdu": parcel["idu"]})
        return {"items": 1, "raw": chosen}

    return await collector.run("apicarto_cadastre", f"address:{address['id']}", task, force=force)


async def get_parcel(idu: str, force: bool = False) -> dict:
    parcel = await db.find_one("parcel", {"idu": idu}, geometry="geom")
    if not parcel or force:

        async def task(stamp: dict) -> dict:
            f = await clients.cadastre_parcel_by_idu(idu)
            if not f:
                raise NotFound(f"Parcelle introuvable : {idu}")
            row = normalize_parcel(f, stamp)
            if not await db.exists("commune", {"inseeCode": row["inseeCode"]}):
                await ensure_commune(row["inseeCode"])
            await db.upsert("parcel", row)
            return {"items": 1, "raw": f}

        outcome = await collector.run("apicarto_cadastre", f"parcel:{idu}", task, force=True)
        if outcome["status"] != "success":
            raise NotFound(outcome.get("error") or f"Parcelle introuvable : {idu}")
        parcel = await db.find_one("parcel", {"idu": idu}, geometry="geom")
    return parcel


# -------------------------------------------------------------- Adresses


async def get_address(address_id: int) -> dict:
    address = await db.find_one("address", {"id": address_id})
    if not address:
        raise NotFound(f"Adresse {address_id} inconnue")
    return address


async def get_address_details(address_id: int) -> dict:
    address = await get_address(address_id)
    commune = await db.find_one("commune", {"inseeCode": address["inseeCode"]})
    parcel = await db.find_one("parcel", {"idu": address["parcelIdu"]}, geometry="geom") if address["parcelIdu"] else None
    return {**address, "commune": commune, "parcel": parcel}


async def list_addresses(insee: str | None, limit: int, offset: int) -> tuple[list[dict], int]:
    where = {"inseeCode": insee} if insee else None
    items = await db.find("address", where, order="t.id DESC", limit=limit, offset=offset)
    return items, await db.count("address", where)


async def link_building(address_id: int, rnb_id: str) -> None:
    await db.update("address", {"id": address_id}, {"rnbId": rnb_id})


async def delete_address(address_id: int) -> None:
    if not await db.delete("address", {"id": address_id}):
        raise NotFound(f"Adresse {address_id} inconnue")


# ------------------------------------------------- Indicateurs d'adresse


async def upsert_indicators(address_id: int, domain: str, items: list[dict], stamp: dict) -> None:
    """`items` : dicts { indicator, valueNum?, valueText?, unit?, details? }."""
    if not items:
        return
    await db.upsert("address_indicator", [
        {
            "addressId": address_id,
            "domain": domain,
            "indicator": i["indicator"],
            "valueNum": i.get("valueNum"),
            "valueText": i.get("valueText"),
            "unit": i.get("unit"),
            "details": i.get("details"),
            **stamp,
        }
        for i in items
    ])


async def indicators_of(address_id: int, domain: str | None = None) -> list[dict]:
    where = {"addressId": address_id, "domain": domain} if domain else {"addressId": address_id}
    return await db.find("address_indicator", where, order="t.domain ASC, t.indicator ASC")
