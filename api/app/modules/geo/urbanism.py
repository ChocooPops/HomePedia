"""Urbanisme : zonage PLU, prescriptions, servitudes d'utilité publique, monuments historiques."""

import math

from ...collector import collector
from ...db import db
from ...geo_utils import distance_to_geometry_meters, haversine_meters, point_in_geometry, square_geojson
from ...parse import chunk, js_round
from . import clients
from .normalizers import normalize_easement, normalize_monument, normalize_plu_zone, normalize_prescription
from .service import point_of

# Codes de prescription PLU utiles à l'analyse (nomenclature CNIG).
PRESCRIPTION_TYPES = {
    "01": "Espace boisé classé",
    "05": "Emplacement réservé",
    "07": "Patrimoine bâti, paysager ou éléments de paysage à protéger",
    "18": "Orientation d’aménagement et de programmation (OAP)",
    "25": "Élément de continuité écologique et trame verte et bleue",
    "35": "Terrain cultivé ou non bâti à protéger en zone urbaine",
}
PROTECTED_LANDSCAPE_TYPES = ("01", "07", "25", "35")

# Rayon (m) de collecte des zones et prescriptions voisines.
NEIGHBOURHOOD_HALF_SIDE_M = 250


async def collect(address: dict, force: bool = False) -> list[dict]:
    p = point_of(address)
    insee = address["inseeCode"]
    area = square_geojson(p, NEIGHBOURHOOD_HALF_SIDE_M)
    target = f"address:{address['id']}"

    async def zones_task(stamp: dict) -> dict:
        features = await clients.gpu_layer("zone-urba", area)
        rows = [normalize_plu_zone(f, insee, stamp) for f in features if f.get("geometry")]
        for c in chunk(rows, 50):
            await db.upsert("plu_zone", c)
        return {"items": len(rows)}

    async def prescriptions_task(stamp: dict) -> dict:
        count = 0
        for layer in ("prescription-surf", "prescription-lin", "prescription-pct"):
            features = await clients.gpu_layer(layer, area)
            rows = [normalize_prescription(f, layer, insee, stamp) for f in features if f.get("geometry")]
            for c in chunk(rows, 50):
                await db.upsert("plu_prescription", c)
            count += len(rows)
        return {"items": count}

    async def easements_task(stamp: dict) -> dict:
        features = await clients.gpu_layer("assiette-sup-s", {"type": "Point", "coordinates": [p["lon"], p["lat"]]})
        rows = [normalize_easement(f, stamp) for f in features if f.get("geometry")]
        for c in chunk(rows, 50):
            await db.upsert("public_easement", c)
        return {"items": len(rows)}

    async def monuments_task(stamp: dict) -> dict:
        raw = await clients.monuments_by_commune(insee)
        rows = [m for m in (normalize_monument(r, stamp) for r in raw) if m]
        for c in chunk(rows, 200):
            await db.upsert("monument", c)
        return {"items": len(rows)}

    return [
        await collector.run("apicarto_gpu", f"{target}:zone-urba", zones_task, force=force),
        await collector.run("apicarto_gpu", f"{target}:prescriptions", prescriptions_task, force=force),
        await collector.run("apicarto_gpu", f"{target}:sup", easements_task, force=force),
        await collector.run("monuments", f"commune:{insee}", monuments_task, force=force),
    ]


def _without_geometry(row: dict, **extra) -> dict:
    return {**{k: v for k, v in row.items() if k != "geometry"}, **extra}


async def read(address: dict, radius_m: int = 250) -> dict:
    """Lecture : zone PLU au point, zones et prescriptions voisines, périmètres MH, monuments proches."""
    p = point_of(address)

    zones = [
        _without_geometry(
            z,
            containsAddress=point_in_geometry(p, z["geometry"]),
            distanceM=js_round(distance_to_geometry_meters(p, z["geometry"])),
        )
        for z in await db.intersects_area("plu_zone", "geom", p, radius_m)
    ]
    zones = sorted((z for z in zones if z["distanceM"] <= radius_m), key=lambda z: z["distanceM"])

    prescriptions = [
        _without_geometry(
            pr,
            typeLabel=PRESCRIPTION_TYPES.get(pr["typeCode"] or ""),
            distanceM=js_round(distance_to_geometry_meters(p, pr["geometry"])),
        )
        for pr in await db.intersects_area("plu_prescription", "geom", p, radius_m)
    ]
    prescriptions = sorted((pr for pr in prescriptions if pr["distanceM"] <= radius_m), key=lambda pr: pr["distanceM"])

    # Une même servitude est souvent publiée en plusieurs exemplaires (un par acte / document) : on dédoublonne.
    seen: set[str] = set()
    easements = []
    for e in await db.intersects_area("public_easement", "geom", p, 1):
        key = f"{e['supType']}|{e['generatorId'] or e['name']}"
        if point_in_geometry(p, e["geometry"]) and key not in seen:
            seen.add(key)
            easements.append(_without_geometry(e))

    monuments = [
        {
            **m,
            "distanceM": js_round(haversine_meters(p, {"lat": m["latitude"], "lon": m["longitude"]}))
            if m["latitude"] is not None and m["longitude"] is not None
            else None,
        }
        for m in await db.find("monument", {"inseeCode": address["inseeCode"]})
    ]
    monuments.sort(key=lambda m: m["distanceM"] if m["distanceM"] is not None else math.inf)

    return {
        "currentZone": next((z for z in zones if z["containsAddress"]), None),
        "neighbouringZones": [z for z in zones if not z["containsAddress"]],
        "reservedLocations": [pr for pr in prescriptions if pr["typeCode"] == "05"],
        "protectedLandscape": [pr for pr in prescriptions if pr["typeCode"] in PROTECTED_LANDSCAPE_TYPES],
        "otherPrescriptions": [pr for pr in prescriptions if pr["typeCode"] not in ("05", *PROTECTED_LANDSCAPE_TYPES)],
        "historicMonumentPerimeter": [e for e in easements if e["supType"] == "ac1"],
        "otherEasements": [e for e in easements if e["supType"] != "ac1"],
        "monuments": monuments[:20],
    }
