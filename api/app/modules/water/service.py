"""Eau : qualité au robinet (Hub'Eau), nappes (piézomètres), restrictions sécheresse (VigiEau)."""

import asyncio
from datetime import datetime, timedelta

from ...collector import collector
from ...db import db
from ...parse import chunk, parse_datetime, utcnow
from ..geo import service as geo
from . import clients
from .clients import WATER_PARAMETERS
from .normalizers import normalize_drought_zone, normalize_groundwater_station, normalize_water

GROUNDWATER_RADIUS_M = 10000
HISTORY_YEARS = 3

# Seuils réglementaires / repères pour l'interprétation.
REFERENCES: dict[str, dict] = {
    "nitrates": {"limit": 50, "unit": "mg/L", "note": "Limite de qualité : 50 mg/L"},
    "total_pesticides": {"limit": 0.5, "unit": "µg/L", "note": "Limite de qualité : 0,5 µg/L (total)"},
    "pfas_sum_20": {"limit": 0.1, "unit": "µg/L", "note": "Limite de qualité : 0,1 µg/L (somme de 20 PFAS, depuis 2026)"},
    "pfas_sum_4": {"unit": "µg/L", "note": "Somme PFOA + PFNA + PFHxS + PFOS"},
    "hardness": {"unit": "°f", "note": "Dureté : < 15 °f eau douce, > 30 °f eau très calcaire"},
}


def _years_ago(years: int) -> datetime:
    """Même jour `years` années plus tôt (un 29 février glisse au 1er mars, comme `setFullYear`)."""
    now = utcnow()
    try:
        return now.replace(year=now.year - years)
    except ValueError:
        return now.replace(year=now.year - years, month=3, day=1)


def _after(value, limit: datetime) -> bool:
    d = parse_datetime(value)
    return d is not None and d > limit


async def collect(address: dict, force: bool = False) -> list[dict]:
    p = geo.point_of(address)
    insee = address["inseeCode"]

    async def quality_task(stamp: dict) -> dict:
        since = _years_ago(HISTORY_YEARS)
        raw = await clients.drinking_water(insee, since.date().isoformat())
        rows = [normalize_water(r, stamp) for r in raw if r.get("code_prelevement") and r.get("date_prelevement")]
        for c in chunk(rows, 300):
            await db.upsert("water_quality_result", c)
        return {"items": len(rows)}

    async def groundwater_task(stamp: dict) -> dict:
        raw = await clients.groundwater_stations(p, GROUNDWATER_RADIUS_M)
        # Dernière mesure pour les stations encore actives les plus proches.
        limit = utcnow() - timedelta(days=2 * 365)
        active = [s for s in raw if s.get("date_fin_mesure") and _after(s["date_fin_mesure"], limit)][:5]
        last_measures: dict[str, dict | None] = {}
        for s in active:
            last_measures[s["code_bss"]] = await clients.last_groundwater_measure(s["code_bss"])

        rows = [
            normalize_groundwater_station(s, last_measures.get(s["code_bss"]), stamp)
            for s in raw
            if s.get("x") and s.get("y")
        ]
        for c in chunk(rows, 200):
            await db.upsert("groundwater_station", c)
        return {"items": len(rows)}

    async def drought_task(stamp: dict) -> dict:
        rows = []
        for zone_type in ("SUP", "SOU", "AEP"):
            for z in await clients.vigieau_zones(p, insee, zone_type):
                rows.append(normalize_drought_zone(z, insee, zone_type, stamp))
        # Les restrictions levées disparaissent de l'API : on remplace l'état de la commune.
        await db.delete("drought_restriction", {"inseeCode": insee})
        if rows:
            await db.upsert("drought_restriction", rows)
        return {"items": len(rows)}

    return list(await asyncio.gather(
        collector.run("hubeau_eau_potable", f"commune:{insee}", quality_task, force=force),
        collector.run("hubeau_nappes", f"address:{address['id']}", groundwater_task, force=force),
        collector.run("vigieau", f"address:{address['id']}", drought_task, force=force),
    ))


async def read(address: dict) -> dict:
    p = geo.point_of(address)
    latest = await db.find(
        "water_quality_result",
        {"inseeCode": address["inseeCode"]},
        where_sql=(
            "t.sampled_at = (SELECT MAX(w2.sampled_at) FROM water_quality_result w2 "
            "WHERE w2.insee_code = t.insee_code AND w2.parameter_code = t.parameter_code)"
        ),
    )

    parameters = []
    for code, key in WATER_PARAMETERS.items():
        r = next((x for x in latest if x["parameterCode"] == code), None)
        ref = REFERENCES.get(key) or {}
        parameters.append({
            "key": key,
            "code": code,
            "label": r["parameterLabel"] if r else None,
            "value": r["resultNumeric"] if r else None,
            "rawValue": r["resultText"] if r else None,
            "unit": r["unit"] if r and r["unit"] is not None else ref.get("unit"),
            "sampledAt": r["sampledAt"] if r else None,
            "exceedsLimit": (
                r["resultNumeric"] > ref["limit"] if r and "limit" in ref and r["resultNumeric"] is not None else None
            ),
            "reference": ref.get("note"),
        })

    by_date = sorted(latest, key=lambda x: x["sampledAt"], reverse=True)
    last_sample = by_date[0] if by_date else {}
    # Stations encore suivies (mesure de moins de 3 ans) d'abord, puis par distance.
    recent_limit = (utcnow() - timedelta(days=3 * 365)).date().isoformat()
    stations = [
        {**s, "active": bool(s["lastMeasureDate"]) and s["lastMeasureDate"] >= recent_limit}
        for s in await db.within_radius("groundwater_station", "location", p, GROUNDWATER_RADIUS_M)
    ]
    stations.sort(key=lambda s: (not s["active"], s["distanceM"]))

    return {
        "drinkingWater": {
            "network": last_sample.get("networkName"),
            "distributor": last_sample.get("distributor"),
            "lastConclusion": last_sample.get("conclusion"),
            "parameters": parameters,
        },
        "drought": await db.find("drought_restriction", {"inseeCode": address["inseeCode"]}),
        "groundwater": stations[:5],
        "sanitation": {"covered": False, "note": "Raccordement à l’assainissement collectif : aucune source ouverte à l’adresse"},
    }


async def history(insee: str, parameter_code: str) -> list[dict]:
    return await db.find(
        "water_quality_result", {"inseeCode": insee, "parameterCode": parameter_code}, order="t.sampled_at ASC"
    )
