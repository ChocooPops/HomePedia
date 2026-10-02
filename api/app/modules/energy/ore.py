"""Agence ORE : consommation annuelle d'électricité et de gaz par commune, agrégée par grand secteur."""

from ...collector import collector
from ...db import db
from ...open_data import datafair_lines
from ...parse import chunk, int_, num, round_to
from ..geo import service as geo

# Le jeu complet pèse plus de 800 Mo en CSV : on l'interroge par commune via l'API data-fair.
ORE_DATASET = "https://opendata.agenceore.fr/data-fair/api/v1/datasets/consommation-annuelle-d-electricite-et-gaz-par-commune"
ORE_FIELDS = "annee,filiere,code_grand_secteur,conso_totale_mwh,nb_sites"
ENERGIES = {"Electricité": "electricity", "Gaz": "gas"}


async def ore_by_commune(insee: str) -> list[dict]:
    return await datafair_lines("agence_ore", ORE_DATASET, {"code_commune_eq": insee, "select": ORE_FIELDS}, 10000)


def normalize_consumption(rows: list[dict], insee: str, stamp: dict) -> list[dict]:
    """Somme des secteurs NAF détaillés par année, énergie et grand secteur (résidentiel, tertiaire, industrie...)."""
    totals: dict[tuple, dict] = {}
    for r in rows:
        year, energy = int_(r.get("annee")), ENERGIES.get(r.get("filiere"))
        if not year or not energy:
            continue
        sector = (r.get("code_grand_secteur") or "INCONNU").upper()[:32]
        t = totals.setdefault((year, energy, sector), {"sites": 0, "mwh": 0.0})
        t["sites"] += int_(r.get("nb_sites")) or 0
        t["mwh"] += num(r.get("conso_totale_mwh")) or 0
    return [
        {
            "inseeCode": insee, "year": year, "energy": energy, "sector": sector,
            "sites": t["sites"], "consumptionMwh": round_to(t["mwh"], 3), **stamp,
        }
        for (year, energy, sector), t in sorted(totals.items())
    ]


async def collect_commune(insee: str, force: bool = False) -> dict:
    await geo.ensure_commune(insee)

    async def task(stamp: dict) -> dict:
        rows = normalize_consumption(await ore_by_commune(insee), insee, stamp)
        for c in chunk(rows, 200):
            await db.upsert("commune_energy_consumption", c)
        return {"items": len(rows)}

    return await collector.run("agence_ore", f"commune:{insee}", task, force=force)


async def read_commune(insee: str) -> dict:
    rows = await db.find("commune_energy_consumption", {"inseeCode": insee}, order="t.year ASC, t.energy ASC, t.sector ASC")
    latest_year = max((r["year"] for r in rows), default=None)
    totals: dict[tuple, float] = {}
    for r in rows:
        totals[(r["year"], r["energy"])] = totals.get((r["year"], r["energy"]), 0) + (r["consumptionMwh"] or 0)
    return {
        "inseeCode": insee,
        "latestYear": latest_year,
        "latest": [r for r in rows if r["year"] == latest_year],
        "totalsByYear": [{"year": y, "energy": e, "consumptionMwh": round_to(v, 3)} for (y, e), v in sorted(totals.items())],
        "bySector": rows,
    }
