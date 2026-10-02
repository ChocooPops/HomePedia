"""Nuisances : sources OSM (bars, lieux de culte, élevages, lignes HT...), plans d'exposition au bruit, survols."""

from ...collector import collector
from ...db import db
from ...geo_utils import bbox_around, distance_to_geometry_meters
from ...open_data import wfs_features
from ...parse import chunk, js_round
from ..connectivity import service as connectivity
from ..geo.service import point_of
from . import clients
from .normalizers import normalize_flight, normalize_line, normalize_peb, normalize_poi, observed_at

DEFAULT_RADIUS_M = 1000
WIDE_RADIUS_M = 3000
FLIGHT_RADIUS_M = 15000
PEB_RADIUS_M = 30000


async def collect(address: dict, force: bool = False, radius_m: int = DEFAULT_RADIUS_M) -> list[dict]:
    p = point_of(address)
    target = f"address:{address['id']}"

    async def osm_task(stamp: dict) -> dict:
        found = await clients.around(p, radius_m, max(WIDE_RADIUS_M, radius_m))
        poi_rows = [r for r in (normalize_poi(e, stamp) for e in found["pois"]) if r is not None]
        line_rows = [r for r in (normalize_line(e, stamp) for e in found["lines"]) if r is not None]
        for c in chunk(poi_rows, 200):
            await db.upsert("nuisance_poi", c)
        for c in chunk(line_rows, 50):
            await db.upsert("nuisance_line", c)
        return {"items": len(poi_rows) + len(line_rows)}

    async def peb_task(stamp: dict) -> dict:
        # La couche nationale DGAC ne publie que le point de l'aérodrome + l'arrêté PEB (pas les zones).
        features = await wfs_features("dgac_peb_arrete_wfs:dgac_peb_arrete_wfs", bbox_around(p, PEB_RADIUS_M), 50)
        rows = [normalize_peb(f, stamp) for f in features if (f.get("geometry") or {}).get("type") == "Point"]
        if rows:
            await db.upsert("nuisance_poi", rows)
        return {"items": len(rows)}

    async def flights_task(stamp: dict) -> dict:
        snapshot = await clients.states(p, FLIGHT_RADIUS_M)
        at = observed_at(snapshot["time"])
        rows = [
            normalize_flight(s, address["id"], p, at, stamp)
            for s in snapshot["states"]
            if s[5] is not None and s[6] is not None
        ]
        if rows:
            await db.upsert("flight_observation", rows)
        return {"items": len(rows)}

    osm = await collector.run("overpass", f"{target}:r{radius_m}", osm_task, force=force)
    peb = await collector.run("geopf_wfs", f"{target}:peb", peb_task, force=force)
    flights = await collector.run("opensky", target, flights_task, force=force)
    return [osm, peb, flights]


async def read(address: dict, radius_m: int = DEFAULT_RADIUS_M) -> dict:
    p = point_of(address)

    nearby = await db.within_radius("nuisance_poi", "location", p, max(radius_m, WIDE_RADIUS_M))
    pebs = await db.within_radius("nuisance_poi", "location", p, PEB_RADIUS_M, {"category": "airport_noise_plan"})

    lines = [
        {**{k: v for k, v in line.items() if k != "geometry"}, "distanceM": js_round(distance_to_geometry_meters(p, line["geometry"]))}
        for line in await db.intersects_area("nuisance_line", "geom", p, WIDE_RADIUS_M)
    ]
    lines = sorted((line for line in lines if line["distanceM"] <= WIDE_RADIUS_M), key=lambda line: line["distanceM"])

    by_category: dict[str, dict] = {}
    for item in [*(n for n in nearby if n["category"] != "airport_noise_plan"), *lines]:
        limit = WIDE_RADIUS_M if item["category"] in ("wind_turbine", "airport", "power_line") else radius_m
        if item["distanceM"] > limit:
            continue
        c = by_category.setdefault(item["category"], {"count": 0, "nearestM": None, "nearest": None})
        c["count"] += 1
        if c["nearestM"] is None or item["distanceM"] < c["nearestM"]:
            c["nearestM"] = item["distanceM"]
            c["nearest"] = {"name": item["name"], "subcategory": item["subcategory"], "distanceM": item["distanceM"]}

    last_observation = await db.find_one("flight_observation", {"addressId": address["id"]}, order="t.observed_at DESC")
    flights = (
        await db.find(
            "flight_observation",
            {"addressId": address["id"], "observedAt": last_observation["observedAt"]},
            order="t.distance_m ASC",
        )
        if last_observation
        else []
    )
    airborne = [f for f in flights if not f["onGround"] and f["altitudeM"] is not None]

    return {
        "radiusM": radius_m,
        "summary": by_category,
        "powerLines": [line for line in lines if line["category"] == "power_line"][:5],
        "mobileAntennas": await connectivity.sites_around(p, 500),
        "airportNoisePlans": pebs[:5],
        "flights": {
            "snapshotAt": last_observation["observedAt"] if last_observation else None,
            "aircraftWithin15km": len(airborne),
            "lowestAltitudeM": min(f["altitudeM"] for f in airborne) if airborne else None,
            "closest": airborne[:5],
            "note": "Instantané OpenSky : à échantillonner dans le temps pour estimer un couloir aérien",
        },
        "notCovered": ["Pollution lumineuse", "Livraisons et fret de nuit", "Odeurs d’épandage", "Cartes de bruit stratégiques (WMS uniquement)"],
    }
