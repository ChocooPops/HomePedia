"""
Connectivité. Les deux sources ARCEP sont des fichiers nationaux (pas d'API à l'adresse) :
on les importe en base puis on interroge localement (index spatial pour les sites mobiles).
"""

import asyncio
import re

from ...collector import collector
from ...db import db
from ...parse import chunk
from ..geo import service as geo
from . import clients
from .normalizers import normalize_fixed, normalize_site, parse_csv

SITES_FILE_PATTERN = re.compile(r'href="([^"]*_sites_(?:Metropole|Outremer)\.csv)"')


async def import_fixed(force: bool = False) -> dict:
    async def task(stamp: dict) -> dict:
        text = await clients.fixed_csv()
        rows = [f for f in (normalize_fixed(r, stamp) for r in parse_csv(text)) if f is not None]
        for c in chunk(rows, 1000):
            await db.upsert("fixed_coverage", c)
        return {"items": len(rows)}

    return await collector.run("arcep_fixe", "france:commune_techno", task, force=force)


async def import_mobile_sites(force: bool = False) -> dict:
    async def task(stamp: dict) -> dict:
        listing = await clients.mobile_listing()
        files = SITES_FILE_PATTERN.findall(listing)
        if not files:
            raise RuntimeError(f"Aucun fichier de sites trouvé dans {clients.MOBILE_DIR}")
        total = 0
        for file in files:
            text = await clients.mobile_sites_csv(file)
            rows = [s for s in (normalize_site(r, stamp) for r in parse_csv(text, relax_column_count=True)) if s is not None]
            for c in chunk(rows, 1000):
                await db.upsert("mobile_site", c)
            total += len(rows)
        return {"items": total, "raw": {"files": files}}

    return await collector.run("arcep_mobile", "france:sites", task, force=force)


async def collect(_address: dict, force: bool = False) -> list[dict]:
    """Collecte « à l'adresse » : s'assure que les deux référentiels nationaux sont chargés et à jour."""
    return [await import_fixed(force), await import_mobile_sites(force)]


async def sites_around(p: dict, radius_m: float) -> list[dict]:
    return await db.within_radius("mobile_site", "location", p, radius_m)


async def read(address: dict) -> dict:
    p = geo.point_of(address)
    fixed, sites = await asyncio.gather(db.find_one("fixed_coverage", {"inseeCode": address["inseeCode"]}), sites_around(p, 3000))

    def summary(op: str) -> dict:
        own = [s for s in sites if s["operatorName"] == op]

        def nearest(key: str):
            return next((s["distanceM"] for s in own if s[key]), None)

        return {
            "operator": op,
            "sitesWithin1km": len([s for s in own if s["distanceM"] <= 1000]),
            "nearest4gM": nearest("has4g"),
            "nearest5gM": nearest("has5g"),
            "nearest5g3500M": nearest("has5g3500"),
        }

    return {
        "fixed": {
            **fixed,
            "scope": "commune",
            "note": "Taux communal d’éligibilité : l’éligibilité exacte du logement n’est pas publiée en API",
        }
        if fixed
        else None,
        "mobile": [summary(op) for op in sorted({s["operatorName"] for s in sites})],
        "note": "Couverture intérieure non mesurée : indicateurs de proximité des sites ARCEP par opérateur",
        "notCovered": ["Réception TNT et satellite à l’adresse"],
    }
