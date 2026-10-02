"""Services de proximité : santé, commerces, crèches, écoles (IPS, effectifs) et temps de trajet."""

import asyncio

from ...collector import collector
from ...db import db
from ...geo_utils import point_wkt
from ...parse import bool_from_flag, chunk, int_, js_round, num, str_
from ..geo import service as geo
from . import clients
from .clients import NAF_CATEGORIES
from .normalizers import normalize_establishment, normalize_osm_service, opens_on_sunday  # noqa: F401 - réexporté

SERVICES_RADIUS_M = 2000
EMERGENCY_RADIUS_M = 30000
SCHOOLS_RADIUS_M = 1500

# Destinations pour lesquelles on calcule un temps de trajet réel (réseau routier IGN).
TRAVEL_TARGETS = [
    {"kind": "nearest_general_practitioner", "category": "general_practitioner", "profiles": ["car", "pedestrian"], "radiusM": SERVICES_RADIUS_M},
    {"kind": "nearest_pharmacy", "category": "pharmacy", "profiles": ["car", "pedestrian"], "radiusM": SERVICES_RADIUS_M},
    {"kind": "nearest_emergency", "category": "emergency", "profiles": ["car"], "radiusM": EMERGENCY_RADIUS_M},
]


def _latest(rows: list[dict], key: str) -> dict:
    m: dict = {}
    for r in rows:
        m.setdefault(r.get(key), r)  # trié par rentrée décroissante
    return m


async def _within_radius(table: str, p: dict, radius_m: float, where: dict | None = None, limit: int | None = None) -> list[dict]:
    """db.within_radius, avec « distanceM » en entier."""
    rows = await db.within_radius(table, "location", p, radius_m, where, limit=limit)
    for r in rows:
        if isinstance(r.get("distanceM"), float):
            r["distanceM"] = js_round(r["distanceM"])
    return rows


async def collect(address: dict, force: bool = False) -> list[dict]:
    p = geo.point_of(address)
    target = f"address:{address['id']}"
    postcode = address.get("postcode")

    async def companies_task(stamp: dict) -> dict:
        raw = await clients.recherche_entreprises_near_point(p, SERVICES_RADIUS_M / 1000, list(NAF_CATEGORIES))
        rows = [r for r in (normalize_establishment(e, stamp) for e in raw) if r is not None]
        for c in chunk(rows, 200):
            await db.upsert("service_place", c)
        return {"items": len(rows)}

    async def osm_task(stamp: dict) -> dict:
        raw = await clients.overpass_around(p, SERVICES_RADIUS_M, EMERGENCY_RADIUS_M)
        rows = [r for r in (normalize_osm_service(e, stamp) for e in raw) if r is not None]
        for c in chunk(rows, 200):
            await db.upsert("service_place", c)
        return {"items": len(rows)}

    async def schools_task(stamp: dict) -> dict:
        raw = await clients.education_schools_around(p, SCHOOLS_RADIUS_M)
        uais = [r.get("identifiant_de_l_etablissement") for r in raw]
        ips_schools, ips_colleges, headcounts = await asyncio.gather(
            clients.education_ips("fr-en-ips-ecoles-ap2022", uais),
            clients.education_ips("fr-en-ips-colleges-ap2023", uais),
            clients.education_headcounts(uais),
        )
        ips = _latest([*ips_schools, *ips_colleges], "uai")
        heads = _latest(headcounts, "numero_ecole")

        rows = []
        for r in raw:
            if not (r.get("latitude") and r.get("longitude")):
                continue
            uai = r.get("identifiant_de_l_etablissement")
            i = ips.get(uai) or {}
            h = heads.get(uai) or {}
            classes = int_(h.get("nombre_total_classes"))
            students = int_(h.get("nombre_total_eleves"))
            rows.append({
                "uai": uai,
                "name": r.get("nom_etablissement"),
                "schoolType": str_(r.get("type_etablissement"), 48),
                "natureLabel": str_(r.get("libelle_nature"), 120),
                "sector": str_(r.get("statut_public_prive"), 16),
                "inseeCode": str_(r.get("code_commune"), 5),
                "hasPreschool": bool_from_flag(r.get("ecole_maternelle")),
                "hasElementary": bool_from_flag(r.get("ecole_elementaire")),
                "hasCanteen": bool_from_flag(r.get("restauration")),
                "priorityEducation": str_(r.get("appartenance_education_prioritaire"), 32),
                "ips": num(i.get("ips")),
                "ipsSchoolYear": str_(i.get("rentree_scolaire"), 9),
                "classesCount": classes,
                "studentsCount": students,
                "avgClassSize": js_round((students / classes) * 10) / 10 if classes and students else None,
                "headcountYear": str_(h.get("rentree_scolaire"), 9),
                "latitude": r["latitude"],
                "longitude": r["longitude"],
                "location": point_wkt(r["longitude"], r["latitude"]),
                **stamp,
            })
        for c in chunk(rows, 200):
            await db.upsert("school", c)
        return {"items": len(rows)}

    async def keyed_health_task(stamp: dict) -> dict:
        count = await clients.fhir_organizations_count(postcode if postcode is not None else "")
        await geo.upsert_indicators(
            address["id"], "services", [{"indicator": "health_organizations_in_postcode", "valueNum": count}], stamp
        )
        return {"items": 1}

    async def keyed_sirene_task(stamp: dict) -> dict:
        count = await clients.sirene_count(address["inseeCode"], "10.71C")
        await geo.upsert_indicators(
            address["id"], "services", [{"indicator": "active_bakeries_in_commune", "valueNum": count}], stamp
        )
        return {"items": 1}

    outcomes = list(await asyncio.gather(
        collector.run("recherche_entreprises", target, companies_task, force=force),
        collector.run("overpass", f"{target}:services", osm_task, force=force),
        collector.run("education", target, schools_task, force=force),
        # Sans code postal, la cible reste « postcode:null » (clé de cache stable).
        collector.run("esante_fhir", f"postcode:{postcode if postcode is not None else 'null'}", keyed_health_task, force=force),
        collector.run("sirene", f"commune:{address['inseeCode']}:bakeries", keyed_sirene_task, force=force),
    ))

    # Temps de trajet réels vers les services les plus proches (après la collecte des lieux).
    async def travel_task(stamp: dict) -> dict:
        count = 0
        for t in TRAVEL_TARGETS:
            found = await _within_radius("service_place", p, t["radiusM"], {"category": t["category"]}, limit=1)
            if not found:
                continue
            nearest = found[0]
            for profile in t["profiles"]:
                route = await clients.ign_navigation_route(p, {"lat": nearest["latitude"], "lon": nearest["longitude"]}, profile)
                await db.upsert("travel_time", {
                    "addressId": address["id"],
                    "destinationKind": t["kind"],
                    "profile": profile,
                    "destinationLabel": nearest["name"] if nearest["name"] is not None else nearest["addressLabel"],
                    "destinationLat": nearest["latitude"],
                    "destinationLon": nearest["longitude"],
                    "durationS": route["durationS"],
                    "distanceM": route["distanceM"],
                    **stamp,
                })
                count += 1
        return {"items": count}

    outcomes.append(await collector.run("ign_navigation", target, travel_task, force=force))
    return outcomes


async def read(address: dict) -> dict:
    p = geo.point_of(address)
    places, emergencies, schools, travel, indicators = await asyncio.gather(
        _within_radius("service_place", p, SERVICES_RADIUS_M),
        _within_radius("service_place", p, EMERGENCY_RADIUS_M, {"category": "emergency"}),
        schools_around(address),
        db.find("travel_time", {"addressId": address["id"]}),
        geo.indicators_of(address["id"], "services"),
    )

    by_category = {}
    for c in sorted({s["category"] for s in places}):
        items = [s for s in places if s["category"] == c]
        by_category[c] = {"countWithin2km": len(items), "nearest": items[:3]}
    bakeries = [s for s in places if s["category"] == "bakery"]

    return {
        "byCategory": by_category,
        "emergency": emergencies[:3],
        "sundayBakeries": [
            b for b in bakeries if isinstance(b.get("details"), dict) and b["details"].get("opensOnSunday") is True
        ][:5],
        "travelTimes": travel,
        "schools": schools,
        "indicators": indicators,
        "notCovered": [
            "Médecins acceptant de nouveaux patients",
            "Pharmacie de garde",
            "Carte scolaire (école de secteur)",
            "Maternités (FINESS non interrogeable par API)",
            "Trajet domicile-travail avec trafic aux heures de pointe",
        ],
    }


async def schools_around(address: dict, radius_m: int = SCHOOLS_RADIUS_M) -> list[dict]:
    return await _within_radius("school", geo.point_of(address), radius_m)


async def places_by_category(insee: str, categories: list[str]) -> list[dict]:
    return await db.find(
        "service_place", {"inseeCode": insee, "category": list(categories)}, order="t.category ASC, t.name ASC"
    )
