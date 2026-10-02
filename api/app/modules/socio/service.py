"""Socio-démographie (recensement, emploi, revenus Filosofi), fiscalité locale et délinquance, à la commune."""

import asyncio
import re

from ...collector import collector
from ...db import db
from ...parse import chunk, js_round
from ..geo import service as geo
from . import clients
from .normalizers import (
    age_bracket_indicators,
    employment_indicators,
    housing_indicators,
    income_indicators,
    normalize_crime,
    normalize_tax,
    population_history_indicators,
    population_indicators,
)

LOGEMENT_TOTALS = {"BUILD_END": "_T", "TDW": "_T", "CARS": "_T", "NRG_SRC": "_T", "TSH": "_T", "CARPARK": "_T", "NOR": "_T"}
# Emploi : ensemble des 15-64 ans, tous sexes et tous niveaux de diplôme.
EMPLOYMENT_FILTERS = {"SEX": "_T", "EDUC": "_T", "AGE": "Y15T64", "RP_MEASURE": "POP"}

# Indicateurs SSMSI mis en avant dans la synthèse.
KEY_CRIME_INDICATORS = [
    re.compile(r"cambriolages", re.IGNORECASE),
    re.compile(r"vols? (sans violence|avec violence)", re.IGNORECASE),
    re.compile(r"violences physiques", re.IGNORECASE),
    re.compile(r"destructions", re.IGNORECASE),
]


async def collect(insee: str, force: bool = False) -> list[dict]:
    await geo.ensure_commune(insee)
    geo_filter = f"COM-{insee}"

    async def census_task(stamp: dict) -> dict:
        population = await clients.melodi_observations("DS_RP_POPULATION_PRINC", {"GEO": geo_filter, "SEX": "_T"})
        occupancy = await clients.melodi_observations(
            "DS_RP_LOGEMENT_PRINC", {"GEO": geo_filter, **LOGEMENT_TOTALS, "L_STAY": "_T", "RP_MEASURE": "DWELLINGS"}
        )
        stay = await clients.melodi_observations("DS_RP_LOGEMENT_PRINC", {"GEO": geo_filter, **LOGEMENT_TOTALS, "OCS": "DW_MAIN"})
        rows = [
            *population_indicators(population, insee, stamp),
            *age_bracket_indicators(population, insee, stamp),
            *housing_indicators(occupancy, stay, insee, stamp),
        ]
        for c in chunk(rows, 200):
            await db.upsert("socio_indicator", c)
        return {"items": len(rows)}

    def melodi_task(dataset: str, filters: dict, normalize):
        async def task(stamp: dict) -> dict:
            rows = normalize(await clients.melodi_observations(dataset, {"GEO": geo_filter, **filters}), insee, stamp)
            for c in chunk(rows, 200):
                await db.upsert("socio_indicator", c)
            return {"items": len(rows)}

        return task

    async def tax_task(stamp: dict) -> dict:
        rows = [t for t in (normalize_tax(r, stamp) for r in await clients.fiscalite_by_commune(insee)) if t is not None]
        if rows:
            await db.upsert("local_tax_rate", rows)
        return {"items": len(rows)}

    async def crime_task(stamp: dict) -> dict:
        rows = [c for c in (normalize_crime(r, insee, stamp) for r in await clients.ssmsi_by_commune(insee)) if c is not None]
        for c in chunk(rows, 200):
            await db.upsert("crime_stat", c)
        return {"items": len(rows)}

    return list(await asyncio.gather(
        collector.run("insee_melodi", f"commune:{insee}", census_task, force=force),
        collector.run(
            "insee_melodi", f"commune:{insee}:history",
            melodi_task("DS_POPULATIONS_HISTORIQUES", {}, population_history_indicators), force=force,
        ),
        collector.run(
            "insee_melodi", f"commune:{insee}:employment",
            melodi_task("DS_RP_EMPLOI_LR_PRINC", EMPLOYMENT_FILTERS, employment_indicators), force=force,
        ),
        collector.run("insee_melodi", f"commune:{insee}:income", melodi_task("DS_FILOSOFI_CC", {}, income_indicators), force=force),
        collector.run("fiscalite_locale", f"commune:{insee}", tax_task, force=force),
        collector.run("ssmsi", f"commune:{insee}", crime_task, force=force),
    ))


async def read(insee: str) -> dict:
    indicators, taxes, crimes = await asyncio.gather(
        db.find("socio_indicator", {"inseeCode": insee}, order="t.indicator ASC, t.year ASC"),
        db.find("local_tax_rate", {"inseeCode": insee}, order="t.year ASC"),
        db.find("crime_stat", {"inseeCode": insee}, order="t.year ASC"),
    )

    series: dict[str, list[dict]] = {}
    for i in indicators:
        series.setdefault(i["indicator"], []).append({"year": i["year"], "value": i["value"], "unit": i["unit"]})
    latest = {k: v[-1] for k, v in series.items()}

    first = taxes[0] if taxes else None
    last = taxes[-1] if taxes else None
    last_crime_year = max(c["year"] for c in crimes) if crimes else None

    return {
        "demography": {"latest": latest, "series": series},
        "taxes": {
            "history": taxes,
            "propertyTaxRateChange": {
                "from": first["year"],
                "to": last["year"],
                "points": js_round((last["propertyTaxRate"] - first["propertyTaxRate"]) * 100) / 100,
            }
            if first and last and first["propertyTaxRate"] is not None and last["propertyTaxRate"] is not None
            else None,
        },
        "crime": {
            "year": last_crime_year,
            "highlights": [
                c for c in crimes
                if c["year"] == last_crime_year and any(r.search(c["indicator"]) for r in KEY_CRIME_INDICATORS)
            ],
            "all": crimes,
        },
        "notCovered": ["Part de locations Airbnb (pas de donnée officielle)", "Vie associative (fichier RNA non interrogeable par API)"],
    }
