"""Mobilité : bornes de recharge, parkings, arrêts de transport, aménagements cyclables, flux GTFS."""

import asyncio
import math
import time

from ...collector import collector
from ...db import db
from ...geo_utils import distance_to_geometry_meters, haversine_meters
from ...parse import chunk, js_round
from ..geo import service as geo
from . import clients
from .normalizers import coverage_level, normalize_charger, normalize_feed, normalize_parking, normalize_stop

STOPS_RADIUS_M = 800
CYCLE_RADIUS_M = 1000

# Catalogue transport.data.gouv mis en cache mémoire (~1 Mo, rafraîchi toutes les 24 h).
_catalog: dict | None = None


async def collect(address: dict, force: bool = False) -> list[dict]:
    p = geo.point_of(address)
    insee = address["inseeCode"]
    target = f"address:{address['id']}"
    commune = await geo.get_commune(insee)

    async def irve_task(stamp: dict) -> dict:
        raw = await clients.irve_by_commune(insee)
        rows = [c for c in (normalize_charger(r, insee, stamp) for r in raw) if c is not None]
        for c in chunk(rows, 300):
            await db.upsert("charging_station", c)
        return {"items": len(rows)}

    async def parking_task(stamp: dict) -> dict:
        raw = await clients.bnls_by_commune(insee)
        rows = [k for k in (normalize_parking(r, insee, stamp) for r in raw) if k is not None]
        if rows:
            await db.upsert("parking_facility", rows)
        return {"items": len(rows)}

    async def osm_task(stamp: dict) -> dict:
        elements = await clients.osm_stops_and_cycleways(p, STOPS_RADIUS_M, CYCLE_RADIUS_M)
        # Les arrêts sortent en « out center » (sans géométrie), les voies cyclables en « out geom ».
        ways = [e for e in elements if e.get("geometry") is not None]

        stop_rows = [s for s in (normalize_stop(e, stamp) for e in elements if e.get("geometry") is None) if s is not None]
        for c in chunk(stop_rows, 200):
            await db.upsert("transit_stop", c)

        # Longueur d'aménagements cyclables dans le rayon (portions de voies à moins de 1 km).
        cycle_meters = 0.0
        for way in ways:
            pts = way["geometry"]
            for i in range(len(pts) - 1):
                mid = {"lat": (pts[i]["lat"] + pts[i + 1]["lat"]) / 2, "lon": (pts[i]["lon"] + pts[i + 1]["lon"]) / 2}
                if haversine_meters(p, mid) <= CYCLE_RADIUS_M:
                    cycle_meters += haversine_meters(pts[i], pts[i + 1])
        nearest_cycle = min(
            (
                distance_to_geometry_meters(p, {"type": "LineString", "coordinates": [[g["lon"], g["lat"]] for g in e["geometry"]]})
                for e in ways
            ),
            default=math.inf,
        )
        await geo.upsert_indicators(address["id"], "mobility", [
            {"indicator": "cycle_infrastructure_within_1km", "valueNum": js_round(cycle_meters), "unit": "m"},
            {
                "indicator": "nearest_cycle_infrastructure",
                "valueNum": js_round(nearest_cycle) if math.isfinite(nearest_cycle) else None,
                "unit": "m",
            },
        ], stamp)
        return {"items": len(stop_rows)}

    async def gtfs_task(stamp: dict) -> dict:
        datasets = await transport_catalog()
        rows = []
        for d in datasets:
            if d.get("type") != "public-transit":
                continue
            level = coverage_level(d.get("covered_area") or [], commune)
            if level is not None:
                rows.append(normalize_feed(d, level, insee, stamp))
        await db.delete("transit_feed", {"inseeCode": insee})
        if rows:
            await db.upsert("transit_feed", rows)
        return {"items": len(rows)}

    return list(await asyncio.gather(
        collector.run("irve", f"commune:{insee}", irve_task, force=force),
        collector.run("bnls", f"commune:{insee}", parking_task, force=force),
        collector.run("overpass", f"{target}:mobility", osm_task, force=force),
        collector.run("transport_gouv", f"commune:{insee}", gtfs_task, force=force),
    ))


async def transport_catalog() -> list[dict]:
    global _catalog
    if not _catalog or time.time() - _catalog["at"] > 86400:
        data = await clients.transport_datasets()
        _catalog = {"at": time.time(), "data": data}
    return _catalog["data"]


async def read(address: dict) -> dict:
    p = geo.point_of(address)
    stops, chargers, parkings, feeds, indicators = await asyncio.gather(
        db.within_radius("transit_stop", "location", p, STOPS_RADIUS_M),
        db.within_radius("charging_station", "location", p, 2000),
        db.within_radius("parking_facility", "location", p, 2000),
        db.find("transit_feed", {"inseeCode": address["inseeCode"]}),
        geo.indicators_of(address["id"], "mobility"),
    )
    modes = list(dict.fromkeys(s["mode"] for s in stops))
    return {
        "transit": {
            "stopsWithin800m": len(stops),
            "byMode": {m: [s for s in stops if s["mode"] == m][:3] for m in modes},
            "gtfsFeeds": feeds,
            "note": "Derniers départs du soir et service du dimanche : à calculer sur les GTFS (traitement batch, hors API)",
        },
        "charging": {
            "pointsWithin2km": len(chargers),
            "fastChargers": len([c for c in chargers if (c["powerKw"] if c["powerKw"] is not None else 0) >= 50]),
            "nearest": chargers[:5],
        },
        "parking": parkings[:5],
        "cycling": {i["indicator"]: {"value": i["valueNum"], "unit": i["unit"]} for i in indicators},
        "notCovered": ["Tarifs et zones de stationnement résident sur voirie"],
    }
