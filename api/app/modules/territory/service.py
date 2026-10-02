"""
Référentiel territorial pour l'analyse à la maille région / département / commune :
régions et départements (API Géo), contours GeoJSON (MongoDB), DVF par département, fiche commune.
"""

import asyncio

from ...collector import collector
from ...db import db
from ...errors import NotFound
from ...mongo import mongo
from ...parse import chunk, utcnow
from ..building import clients as building_clients
from ..building import normalizers as building_normalizers
from ..building import service as building
from ..energy import ore
from ..geo import service as geo
from ..listings import service as listings
from ..reviews import service as reviews
from ..risk import service as risk
from ..socio import service as socio
from . import clients

LEVELS = ("region", "department", "commune")


def department_of(insee: str) -> str:
    """« 80021 » -> « 80 », « 97411 » -> « 974 », « 2A004 » -> « 2A »."""
    return insee[:3] if insee.startswith(("97", "98")) else insee[:2]


# ------------------------------------------------------------ Référentiel


async def collect_reference(force: bool = False) -> list[dict]:
    """Régions et départements (API Géo) et leurs contours simplifiés (france-geojson)."""

    async def regions_task(stamp: dict) -> dict:
        rows = [{"code": r["code"], "name": r["nom"], **stamp} for r in await clients.geo_api_regions()]
        await db.upsert("region", rows)
        return {"items": len(rows)}

    async def departments_task(stamp: dict) -> dict:
        rows = [
            {"code": d["code"], "name": d["nom"], "regionCode": d["codeRegion"], **stamp}
            for d in await clients.geo_api_departments()
        ]
        await db.upsert("department", rows)
        return {"items": len(rows)}

    def contours_task(level: str):
        async def task(stamp: dict) -> dict:
            features = await clients.france_geojson(level)
            parents = {d["code"]: d["regionCode"] for d in await db.find("department")} if level == "department" else {}
            docs = [
                {
                    "level": level, "code": f["properties"]["code"], "name": f["properties"]["nom"],
                    "parentCode": parents.get(f["properties"]["code"]), "geometry": f["geometry"],
                }
                for f in features
                if f.get("geometry")
            ]
            await _save_contours(docs, stamp)
            return {"items": len(docs)}

        return task

    outcomes = [
        await collector.run("geo_api", "reference:regions", regions_task, force=force),
        await collector.run("geo_api", "reference:departments", departments_task, force=force),
    ]
    outcomes += await asyncio.gather(
        collector.run("france_geojson", "contours:regions", contours_task("region"), force=force),
        collector.run("france_geojson", "contours:departments", contours_task("department"), force=force),
    )
    return outcomes


async def list_regions() -> list[dict]:
    return await db.find("region", order="t.name ASC")


async def list_departments(region: str | None = None) -> list[dict]:
    return await db.find("department", {"regionCode": region} if region else None, order="t.code ASC")


# ---------------------------------------------------------------- Contours


async def _save_contours(docs: list[dict], stamp: dict) -> None:
    for doc in docs:
        await mongo.contours.update_one(
            {"level": doc["level"], "code": doc["code"]},
            {"$set": {**doc, "sourceCode": stamp["sourceCode"], "fetchedAt": stamp["fetchedAt"]}},
            upsert=True,
        )


async def collect_commune_contours(dep: str, force: bool = False) -> dict:
    """Contours de toutes les communes d'un département (API Géo)."""

    async def task(stamp: dict) -> dict:
        docs = [
            {
                "level": "commune", "code": f["properties"]["code"], "name": f["properties"]["nom"], "parentCode": dep,
                "population": f["properties"].get("population"), "geometry": f["geometry"],
            }
            for f in await clients.geo_api_commune_contours(dep)
            if f.get("geometry")
        ]
        await _save_contours(docs, stamp)
        return {"items": len(docs)}

    return await collector.run("geo_api", f"department:{dep}:contours", task, force=force)


async def collect_commune_contour(insee: str, force: bool = False) -> dict:
    async def task(stamp: dict) -> dict:
        c = await clients.geo_api_commune_contour(insee)
        if not c:
            raise NotFound(f"Contour introuvable pour la commune {insee}")
        doc = {
            "level": "commune", "code": c["code"], "name": c["nom"], "parentCode": department_of(insee),
            "population": c.get("population"), "geometry": c["contour"],
        }
        await _save_contours([doc], stamp)
        return {"items": 1}

    return await collector.run("geo_api", f"commune:{insee}:contour", task, force=force)


async def contours(level: str, parent: str | None = None) -> dict:
    """FeatureCollection GeoJSON des contours d'un niveau (filtré par région ou département parent)."""
    criteria = {"level": level} | ({"parentCode": parent} if parent else {})
    features = [
        {
            "type": "Feature",
            "geometry": c["geometry"],
            "properties": {k: c.get(k) for k in ("code", "name", "parentCode", "population") if c.get(k) is not None},
        }
        async for c in mongo.contours.find(criteria, {"_id": 0}).sort("code")
    ]
    return {"type": "FeatureCollection", "features": features}


async def contour_of(level: str, code: str) -> dict | None:
    doc = await mongo.contours.find_one({"level": level, "code": code}, {"_id": 0, "geometry": 1})
    return doc["geometry"] if doc else None


# ------------------------------------------------------ DVF par département


async def collect_department_dvf(dep: str, years: list[int] | None = None, force: bool = False) -> list[dict]:
    """
    Import DVF d'un département entier (par défaut la dernière année publiée),
    puis recalcul de l'indice de prix de chacune de ses communes.
    """
    target_years = years or [max(await building_clients.dvf_available_years())]
    outcomes: list[dict] = []
    for year in target_years:

        async def task(stamp: dict, year: int = year) -> dict:
            raw = await clients.dvf_department_year(dep, year)
            rows = [row for row in (building_normalizers.normalize_dvf_row(r, stamp) for r in raw) if row is not None]
            for c in chunk(rows, 500):
                await db.upsert("dvf_mutation", c)
            return {"items": len(rows)}

        outcomes.append(await collector.run("dvf", f"department:{dep}:{year}", task, force=force))

    if any(o["status"] == "success" for o in outcomes):
        communes = await db.query(
            "SELECT DISTINCT insee_code FROM dvf_mutation WHERE insee_code LIKE :prefix", {"prefix": f"{dep}%"}
        )
        slots = asyncio.Semaphore(6)

        async def recompute(insee: str):
            async with slots:
                await building.compute_price_index(insee)

        await asyncio.gather(*(recompute(c["insee_code"]) for c in communes if department_of(c["insee_code"]) == dep))
    return outcomes


async def department_prices(dep: str, year: int | None = None, property_type: str = "Ensemble") -> dict:
    """Prix au m² médian de chaque commune du département (indice calculé à partir des ventes DVF stockées)."""
    years = await db.query(
        "SELECT DISTINCT year FROM price_index WHERE insee_code LIKE :prefix AND property_type = :type ORDER BY year",
        {"prefix": f"{dep}%", "type": property_type},
    )
    available = [y["year"] for y in years]
    year = year or (available[-1] if available else None)
    rows = await db.query(
        "SELECT p.insee_code, c.name, p.sales_count, p.median_price_m2, p.mean_price_m2, p.q1_price_m2, p.q3_price_m2 "
        "FROM price_index p LEFT JOIN commune c ON c.insee_code = p.insee_code "
        "WHERE p.insee_code LIKE :prefix AND p.property_type = :type AND p.year = :year ORDER BY p.insee_code",
        {"prefix": f"{dep}%", "type": property_type, "year": year},
    ) if year else []
    return {
        "department": dep,
        "year": year,
        "availableYears": available,
        "propertyType": property_type,
        "communes": [
            {
                "inseeCode": r["insee_code"], "name": r["name"], "salesCount": r["sales_count"],
                "medianPriceM2": r["median_price_m2"], "meanPriceM2": r["mean_price_m2"],
                "q1PriceM2": r["q1_price_m2"], "q3PriceM2": r["q3_price_m2"],
            }
            for r in rows
            if department_of(r["insee_code"]) == dep
        ],
    }


# ------------------------------------------------------------ Fiche commune


async def collect_commune(insee: str, force: bool = False) -> dict:
    """Collecte tout ce qui se rattache à la commune : contour, recensement, revenus, DVF, énergie."""
    started = utcnow()
    outcomes = [await geo.ensure_commune(insee, force)]

    async def safe(collecting) -> list[dict]:
        try:
            result = await collecting
        except Exception as err:  # noqa: BLE001 - une source en panne n'interrompt pas les autres
            return [{"source": "internal", "target": f"commune:{insee}", "status": "error", "items": 0, "error": str(err)}]
        return result if isinstance(result, list) else [result]

    groups = await asyncio.gather(
        safe(collect_commune_contour(insee, force)),
        safe(socio.collect(insee, force)),
        safe(building.collect_dvf(insee, None, force)),
        safe(ore.collect_commune(insee, force)),
    )
    outcomes += [o for group in groups for o in group]
    statuses = [o["status"] for o in outcomes]
    return {
        "inseeCode": insee,
        "durationMs": int((utcnow() - started).total_seconds() * 1000),
        "summary": {s: statuses.count(s) for s in ("success", "cached", "skipped", "error")},
        "outcomes": outcomes,
    }


async def commune_report(insee: str) -> dict:
    """Fiche commune consolidée (lecture seule, à partir des bases)."""
    commune = await db.find_one("commune", {"inseeCode": insee})
    if not commune:
        raise NotFound(f"Commune {insee} non enregistrée : lancer la collecte de la commune")
    socio_data, prices, listing_stats, energy, catnat, risk_profile, review_summary, contour = await asyncio.gather(
        socio.read(insee),
        building.price_index(insee),
        listings.commune_stats(insee),
        ore.read_commune(insee),
        risk.catnat_of(insee),
        db.find_one("commune_risk_profile", {"inseeCode": insee}),
        reviews.summary(insee),
        contour_of("commune", insee),
    )
    return {
        "commune": {**commune, "contour": contour},
        "socio": socio_data,
        "market": {"priceIndex": prices, "listings": listing_stats},
        "energy": energy,
        "risks": {"profile": risk_profile, "catnat": catnat},
        "reviews": review_summary,
        "generatedAt": utcnow(),
    }


# ------------------------------------------------------------ Vue d'ensemble


async def overview() -> dict:
    """Volumes stockés et état des sources, pour le tableau de bord."""
    tables = ("address", "commune", "dvf_mutation", "price_index", "dpe_certificate", "socio_indicator", "school", "service_place")
    counts = await asyncio.gather(*(db.count(t) for t in tables))
    sources = await db.query("SELECT domain, status, COUNT(*) AS n FROM data_source GROUP BY domain, status ORDER BY domain")
    logs = await db.query(
        "SELECT status, COUNT(*) AS n, MAX(fetched_at) AS last_at FROM fetch_log "
        "WHERE fetched_at > :since GROUP BY status",
        {"since": utcnow().replace(hour=0, minute=0, second=0, microsecond=0)},
    )
    return {
        "tables": dict(zip(tables, counts, strict=True)),
        "documents": {
            "listings": await mongo.listings.estimated_document_count(),
            "reviews": await mongo.reviews.estimated_document_count(),
            "contours": await mongo.contours.estimated_document_count(),
            "rawPayloads": await mongo.raw_payloads.estimated_document_count(),
        },
        "sources": sources,
        "collectsToday": logs,
    }
