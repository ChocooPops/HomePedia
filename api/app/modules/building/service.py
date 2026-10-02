"""Bâtiment (RNB, BDNB), DPE, copropriété (RNIC), ventes DVF et indice de prix."""

import json

from ...collector import collector
from ...db import db
from ...geo_utils import bbox_around, haversine_meters
from ...parse import chunk, js_round
from ..geo import service as geo
from . import clients, normalizers

DPE_RADIUS_M = 30

_BBOX_SQL = "t.latitude BETWEEN :minLat AND :maxLat AND t.longitude BETWEEN :minLon AND :maxLon"


# ------------------------------------------------------------- Collecte


async def collect(address: dict, force: bool = False) -> list[dict]:
    p = geo.point_of(address)
    target = f"address:{address['id']}"
    outcomes: list[dict] = []

    async def rnb_task(stamp: dict) -> dict:
        candidates = await clients.rnb_closest(p, 30)
        # On privilégie le bâtiment qui porte l'adresse BAN, sinon le plus proche.
        chosen = next(
            (b for b in candidates if any(a.get("id") == address["banId"] for a in b.get("addresses") or [])),
            candidates[0] if candidates else None,
        )
        if not chosen:
            return {"items": 0, "raw": candidates}
        await db.upsert("building", normalizers.normalize_rnb(chosen, address["inseeCode"], stamp))
        await geo.link_building(address["id"], chosen["rnb_id"])
        address["rnbId"] = chosen["rnb_id"]
        return {"items": 1, "raw": chosen}

    outcomes.append(await collector.run("rnb", target, rnb_task, force=force))

    if address.get("rnbId"):
        rnb_id = address["rnbId"]

        async def bdnb_task(_stamp: dict) -> dict:
            group_id = await clients.bdnb_group_id_for_rnb(rnb_id)
            if not group_id:
                return {"items": 0}
            group = await clients.bdnb_group(group_id)
            if not group:
                return {"items": 0}
            await db.update("building", {"rnbId": rnb_id}, normalizers.normalize_bdnb(group))
            return {"items": 1, "raw": group}

        outcomes.append(await collector.run("bdnb", f"rnb:{rnb_id}", bdnb_task, force=force))

    async def dpe_task(stamp: dict) -> dict:
        raw = await clients.dpe_near(p, DPE_RADIUS_M)
        rows = [normalizers.normalize_dpe(d, stamp) for d in raw if d.get("numero_dpe")]
        for c in chunk(rows, 200):
            await db.upsert("dpe_certificate", c)
        return {"items": len(rows)}

    outcomes.append(await collector.run("ademe_dpe", target, dpe_task, force=force))

    building = await db.find_one("building", {"rnbId": address["rnbId"]}) if address.get("rnbId") else None

    async def rnic_task(stamp: dict) -> dict:
        raw: list[dict] = []
        if building and building["condoRegistration"]:
            raw = await clients.rnic_by_registration(building["condoRegistration"])
        if not raw and address.get("parcelIdu"):
            raw = await clients.rnic_by_parcel(address["parcelIdu"])
        rows = [normalizers.normalize_rnic(r, stamp) for r in raw if r.get("numero_d_immatriculation")]
        if rows:
            await db.upsert("condominium", rows)
        return {"items": len(rows)}

    outcomes.append(await collector.run("rnic", target, rnic_task, force=force))

    outcomes.extend(await collect_dvf(address["inseeCode"], None, force))
    return outcomes


async def collect_dvf(insee: str, years: list[int] | None = None, force: bool = False) -> list[dict]:
    """Import DVF d'une commune (toutes les années publiées par défaut) puis recalcul de l'indice de prix."""
    await geo.ensure_commune(insee)
    target_years = years if years else await clients.dvf_available_years()
    outcomes: list[dict] = []
    for year in target_years:

        async def task(stamp: dict, year: int = year) -> dict:
            raw = await clients.dvf_commune_year(insee, year)
            rows = [row for row in (normalizers.normalize_dvf_row(r, stamp) for r in raw) if row is not None]
            for c in chunk(rows, 500):
                await db.upsert("dvf_mutation", c)
            return {"items": len(rows)}

        outcomes.append(await collector.run("dvf", f"commune:{insee}:{year}", task, force=force))
    if any(o["status"] == "success" for o in outcomes):
        await compute_price_index(insee)
    return outcomes


async def compute_price_index(insee: str) -> list[dict]:
    rows = await db.find("dvf_mutation", {"inseeCode": insee, "nature": "Vente"})
    index = normalizers.compute_price_index(rows)
    await db.delete("price_index", {"inseeCode": insee})
    if index:
        await db.upsert("price_index", index)
    return sorted(index, key=lambda i: (i["year"], i["propertyType"]))


# -------------------------------------------------------------- Lecture


async def read(address: dict) -> dict:
    building = await db.find_one("building", {"rnbId": address["rnbId"]}) if address.get("rnbId") else None

    p = geo.point_of(address)
    clauses = [f"({_BBOX_SQL})"]
    params: dict = dict(bbox_around(p, DPE_RADIUS_M))
    if address.get("rnbId"):
        clauses.insert(0, "t.rnb_id = :rnbId")
        params["rnbId"] = address["rnbId"]
    if address.get("banId"):
        clauses.insert(0, "t.ban_id = :banId")
        params["banId"] = address["banId"]
    candidates = await db.find(
        "dpe_certificate", where_sql=" OR ".join(clauses), params=params, order="t.issued_at DESC", limit=200
    )
    dpes = [
        {
            **d,
            "sameAddress": d["banId"] == address["banId"],
            "distanceM": js_round(haversine_meters(p, {"lat": d["latitude"], "lon": d["longitude"]}))
            if d["latitude"] is not None and d["longitude"] is not None
            else None,
        }
        for d in candidates
    ]
    reference = next((d for d in dpes if d["sameAddress"]), dpes[0] if dpes else None)

    if building and building["condoRegistration"]:
        condo = await db.find_one("condominium", {"registrationNumber": building["condoRegistration"]})
    elif address.get("parcelIdu"):
        condo = await db.find_one(
            "condominium", where_sql="JSON_CONTAINS(t.cadastral_refs, :ref)", params={"ref": json.dumps(address["parcelIdu"])}
        )
    else:
        condo = None

    year = building["constructionYear"] if building else None
    if year is None and reference:
        year = reference["constructionYear"]
    return {
        "building": building,
        "dpe": {"reference": reference, "all": dpes},
        "condominium": condo,
        "ceilingHeightM": reference["ceilingHeightM"] if reference else None,
        "presumptions": normalizers.building_presumptions(year, reference["energyClass"] if reference else None),
    }


async def price_index(insee: str) -> list[dict]:
    return await db.find("price_index", {"inseeCode": insee}, order="t.year ASC, t.property_type ASC")


async def list_mutations(insee: str, year: int | None, type_: str | None, page: int, limit: int) -> dict:
    clauses: list[str] = []
    params: dict = {}
    if year:
        clauses.append("t.mutation_date BETWEEN :from AND :to")
        params |= {"from": f"{year}-01-01", "to": f"{year}-12-31"}
    if type_:
        clauses.append("t.property_type = :type")
        params["type"] = type_
    where_sql = " AND ".join(clauses) or None
    items = await db.find(
        "dvf_mutation", {"inseeCode": insee}, where_sql=where_sql, params=params,
        order="t.mutation_date DESC", limit=limit, offset=(page - 1) * limit,
    )
    total = await db.count("dvf_mutation", {"inseeCode": insee}, where_sql=where_sql, params=params)
    return {"total": total, "page": page, "limit": limit, "items": items}


async def mutations_around(address: dict, radius_m: float) -> list[dict]:
    """Ventes autour d'une adresse (rayon en mètres)."""
    p = geo.point_of(address)
    rows = await db.find(
        "dvf_mutation", where_sql=_BBOX_SQL, params=bbox_around(p, radius_m), order="t.mutation_date DESC", limit=1000
    )
    out = []
    for r in rows:
        distance = js_round(haversine_meters(p, {"lat": r["latitude"], "lon": r["longitude"]}))
        if distance > radius_m:
            continue
        price_m2 = js_round(r["priceEur"] / r["builtAreaM2"]) if r["priceEur"] and r["builtAreaM2"] else None
        out.append({**r, "priceM2": price_m2, "distanceM": distance})
    return out
