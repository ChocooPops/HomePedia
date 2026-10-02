"""Risques à l'adresse : rapport Géorisques, profil communal, CatNat, sites proches, OLD, risques biologiques."""

import asyncio
import re

from ...collector import collector
from ...db import db
from ...geo_utils import bbox_around, point_in_geometry
from ...open_data import wfs_features
from ...parse import chunk, js_round
from ..geo import service as geo
from . import clients
from .normalizers import (
    normalize_catnat,
    normalize_cavity,
    normalize_commune_profile,
    normalize_ground_movement,
    normalize_installation,
    normalize_polluted_soils,
    normalize_report,
)

SITES_RADIUS_M = 1000
ICPE_RADIUS_M = 3000


async def collect(address: dict, force: bool = False) -> list[dict]:
    p = geo.point_of(address)
    target = f"address:{address['id']}"
    insee = address["inseeCode"]

    async def report(stamp: dict) -> dict:
        raw = await clients.report(p)
        rows = normalize_report(raw, address["id"], stamp)
        if rows:
            await db.upsert("risk_assessment", rows)
        return {"items": len(rows), "raw": raw}

    async def profile(stamp: dict) -> dict:
        radon, seismic, risks, azi = await asyncio.gather(
            clients.radon(insee),
            clients.seismic_zone(insee),
            clients.commune_risks(insee),
            clients.flood_atlases(insee),
        )
        await db.upsert("commune_risk_profile", normalize_commune_profile(insee, radon, seismic, risks, azi, stamp))
        return {"items": 1, "raw": {"radon": radon, "seismic": seismic, "risks": risks, "azi": azi}}

    async def catnat(stamp: dict) -> dict:
        raw = await clients.catnat(insee)
        rows = [normalize_catnat(r, stamp) for r in raw if r.get("code_national_catnat")]
        for c in chunk(rows, 200):
            await db.upsert("catnat_decree", c)
        return {"items": len(rows)}

    async def sites(stamp: dict) -> dict:
        cavities, movements, soils, icpe = await asyncio.gather(
            clients.cavities(p, SITES_RADIUS_M),
            clients.ground_movements(p, SITES_RADIUS_M),
            clients.polluted_soils(p, SITES_RADIUS_M),
            clients.installations(p, ICPE_RADIUS_M),
        )
        rows = [
            *(normalize_cavity(r, stamp) for r in cavities),
            *(normalize_ground_movement(r, stamp) for r in movements),
            *normalize_polluted_soils(soils, stamp),
            *(normalize_installation(r, stamp) for r in icpe),
        ]
        rows = [r for r in rows if r is not None]
        for c in chunk(rows, 200):
            await db.upsert("risk_site", c)
        return {"items": len(rows)}

    # Obligations légales de débroussaillement (couche nationale IGN, WFS).
    async def old(stamp: dict) -> dict:
        features = await wfs_features("DEBROUSSAILLEMENT:debroussaillement", bbox_around(p, 50), 20)
        hit = next((f for f in features if point_in_geometry(p, f.get("geometry"))), None)
        details = None
        if hit:
            props = hit["properties"]
            keys = {"source": "source", "millesime": "millesime", "url": "url", "arrete": "dat_ap_old"}
            details = {out: props[key] for out, key in keys.items() if key in props}
        await db.upsert("risk_assessment", {
            "addressId": address["id"],
            "hazardCode": "obligationDebroussaillement",
            "category": "regulatory",
            "label": "Obligation légale de débroussaillement (OLD)",
            "present": bool(hit),
            "communeStatus": None,
            "addressStatus": "Zone soumise aux OLD" if hit else "Hors zone OLD connue",
            "details": details,
            **stamp,
        })
        return {"items": 1 if hit else 0}

    return list(await asyncio.gather(
        collector.run("georisques", f"{target}:report", report, force=force),
        collector.run("georisques", f"commune:{insee}:profile", profile, force=force),
        collector.run("georisques", f"commune:{insee}:catnat", catnat, force=force),
        collector.run("georisques", f"{target}:sites", sites, force=force),
        collector.run("geopf_wfs", f"{target}:debroussaillement", old, force=force),
    ))


async def read(address: dict, radius_m: int = SITES_RADIUS_M) -> dict:
    p = geo.point_of(address)
    commune = await geo.get_commune(address["inseeCode"])
    assessments, profile, catnat, nearby_sites, bio = await asyncio.gather(
        db.find("risk_assessment", {"addressId": address["id"]}, order="t.category ASC, t.hazard_code ASC"),
        db.find_one("commune_risk_profile", {"inseeCode": address["inseeCode"]}),
        catnat_of(address["inseeCode"]),
        db.within_radius("risk_site", "location", p, max(radius_m, ICPE_RADIUS_M)),
        db.find(
            "bio_risk",
            where_sql="(t.scope = 'commune' AND t.area_code = :insee) OR (t.scope = 'department' AND t.area_code = :department)",
            params={"insee": address["inseeCode"], "department": commune["departmentCode"]},
            order="t.year DESC",
        ),
    )

    # ROUND(...) revient de MariaDB en flottant : distance entière, comme en sortie de l'ancienne API.
    nearby_sites = [{**s, "distanceM": js_round(s["distanceM"])} for s in nearby_sites]

    def sites_by_type(site_type: str, max_m: int) -> list[dict]:
        return [s for s in nearby_sites if s["siteType"] == site_type and s["distanceM"] <= max_m]

    by_hazard: dict[str, int] = {}
    for c in catnat:
        by_hazard[c["hazardLabel"]] = by_hazard.get(c["hazardLabel"], 0) + 1

    return {
        "atAddress": [a for a in assessments if a["present"]],
        "notPresent": [a["hazardCode"] for a in assessments if not a["present"]],
        "commune": profile,
        "catnat": {"total": len(catnat), "byHazard": by_hazard, "latest": catnat[:10]},
        "sites": {
            "seveso": [
                s for s in nearby_sites
                if s["siteType"] == "icpe" and s["sevesoStatus"] and not re.search("non", s["sevesoStatus"], re.IGNORECASE)
            ],
            "icpe": sites_by_type("icpe", ICPE_RADIUS_M)[:50],
            "pollutedSoils": [*sites_by_type("casias", radius_m), *sites_by_type("ssp", radius_m)],
            "cavities": sites_by_type("cavity", radius_m),
            "groundMovements": sites_by_type("ground_movement", radius_m),
        },
        "biological": bio,
    }


async def catnat_of(insee: str) -> list[dict]:
    return await db.find("catnat_decree", {"inseeCode": insee}, order="t.event_start DESC")


# --------------------------------------------- Risques biologiques (saisie manuelle)


async def upsert_bio_risks(items: list[dict]) -> None:
    """
    `items` : dicts { scope, areaCode, species, status, year, referenceUrl?, notes? }.
    Une propriété facultative absente de tous les éléments n'est pas écrasée en base ;
    renseignée dans au moins un élément, elle vaut NULL pour les autres.
    """
    stamp = collector.stamp("manual")
    keys = list(dict.fromkeys(k for i in items for k in i))
    await db.upsert("bio_risk", [{**{k: i.get(k) for k in keys}, **stamp} for i in items])


async def list_bio_risks(area_code: str | None = None, species: str | None = None) -> list[dict]:
    where: dict = {}
    if area_code:
        where["areaCode"] = area_code
    if species:
        where["species"] = species.split(",")
    return await db.find("bio_risk", where, order="t.area_code ASC, t.species ASC, t.year DESC")
