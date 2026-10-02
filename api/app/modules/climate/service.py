"""Climat observé (10 ans), projections 2041-2050, potentiel solaire, qualité de l'air et pollens."""

import asyncio
from datetime import datetime

from ...collector import collector
from ...db import db
from ...parse import int_, js_round, num, str_, utcnow
from ..geo import service as geo
from . import clients
from .clients import CLIMATE_MODELS
from .normalizers import climate_indicators, projection_indicators

# Période de référence modélisée vs horizon 2050 (l'API s'arrête au 31/12/2050).
PERIODS = [
    {"key": "2005-2014", "start": "2005-01-01", "end": "2014-12-31"},
    {"key": "2041-2050", "start": "2041-01-01", "end": "2050-12-31"},
]


def _or(value, default):
    """Équivalent de `value ?? default`."""
    return default if value is None else value


async def collect(address: dict, force: bool = False) -> list[dict]:
    p = geo.point_of(address)
    target = f"address:{address['id']}"

    async def history_task(stamp: dict) -> dict:
        last_year = datetime.now().year - 1
        res = await clients.open_meteo_archive(p, f"{last_year - 9}-01-01", f"{last_year}-12-31")
        meta = {
            "period": f"{last_year - 9}-{last_year}",
            "gridLat": res.get("latitude"),
            "gridLon": res.get("longitude"),
            "elevation": res.get("elevation"),
        }
        items = climate_indicators(res["daily"], meta)
        await geo.upsert_indicators(address["id"], "climate", items, stamp)
        return {"items": len(items), "raw": {"meta": meta, "units": res.get("daily_units")}}

    async def projection_task(stamp: dict) -> dict:
        rows = []
        for period in PERIODS:
            res = await clients.open_meteo_climate(p, period["start"], period["end"])
            for model in CLIMATE_MODELS:
                for i in projection_indicators(res["daily"], model):
                    rows.append({
                        "addressId": address["id"], "model": model, "period": period["key"],
                        "indicator": i["indicator"], "value": i["value"], "unit": i["unit"], **stamp,
                    })
        if rows:
            await db.upsert("climate_projection", rows)
        return {"items": len(rows)}

    async def solar_task(stamp: dict) -> dict:
        res = await clients.pvgis_pvcalc(p)
        outputs = res.get("outputs") or {}
        fixed = ((res.get("inputs") or {}).get("mounting_system") or {}).get("fixed") or {}
        totals = (outputs.get("totals") or {}).get("fixed") or {}
        monthly = [
            {"month": m.get("month"), "kwh": m.get("E_m"), "irradiation": m.get("H(i)_m")}
            for m in (outputs.get("monthly") or {}).get("fixed") or []
        ]
        winter = sum(m["kwh"] for m in monthly if m["month"] in (12, 1, 2))
        await db.upsert("solar_potential", {
            "addressId": address["id"],
            "tiltDeg": _or(int_((fixed.get("slope") or {}).get("value")), 35),
            "azimuthDeg": _or(int_((fixed.get("azimuth") or {}).get("value")), 0),
            "yearlyKwhPerKwp": num(totals.get("E_y")),
            "yearlyIrradiationKwhM2": num(totals.get("H(i)_y")),
            "winterKwhPerKwp": js_round(winter * 100) / 100,
            "monthly": monthly,
            **stamp,
        })
        return {"items": 1, "raw": outputs.get("totals")}

    async def air_task(stamp: dict) -> dict:
        today = utcnow().date().isoformat()
        rows = []
        for kind in ("atmo", "pollens"):
            for f in await clients.atmo_indices(kind, address["inseeCode"], today):
                pr = f.get("properties") or {}
                rows.append({
                    "inseeCode": address["inseeCode"],
                    "indexType": "atmo" if kind == "atmo" else "pollen",
                    "indexDate": str(_or(pr.get("date_ech"), today))[:10],
                    "levelCode": int_(pr.get("code_qual")),
                    "levelLabel": str_(pr.get("lib_qual"), 48),
                    "responsible": str_(pr.get("pollen_resp"), 120),
                    "details": pr,
                    **stamp,
                })
        if rows:
            await db.upsert("air_quality_index", rows)
        return {"items": len(rows)}

    return list(await asyncio.gather(
        collector.run("open_meteo_archive", target, history_task, force=force),
        collector.run("open_meteo_climate", target, projection_task, force=force),
        collector.run("pvgis", target, solar_task, force=force),
        collector.run("atmo", f"commune:{address['inseeCode']}", air_task, force=force),
    ))


async def read(address: dict) -> dict:
    indicators, projections, solar, air = await asyncio.gather(
        geo.indicators_of(address["id"], "climate"),
        db.find("climate_projection", {"addressId": address["id"]}),
        db.find("solar_potential", {"addressId": address["id"]}),
        db.find("air_quality_index", {"inseeCode": address["inseeCode"]}, order="t.index_date DESC", limit=14),
    )

    # Moyenne multi-modèles et écart futur - passé pour chaque indicateur.
    ensemble: dict[str, dict[str, float | None]] = {}
    for indicator in dict.fromkeys(x["indicator"] for x in projections):
        ensemble[indicator] = {}
        for period in PERIODS:
            vals = [
                x["value"] for x in projections
                if x["indicator"] == indicator and x["period"] == period["key"] and x["value"] is not None
            ]
            ensemble[indicator][period["key"]] = js_round(sum(vals) / len(vals) * 10) / 10 if vals else None
        past, future = (ensemble[indicator][period["key"]] for period in PERIODS)
        ensemble[indicator]["change"] = js_round((future - past) * 10) / 10 if past is not None and future is not None else None

    return {
        "observed": {i["indicator"]: {"value": i["valueNum"], "unit": i["unit"]} for i in indicators},
        "observedMeta": indicators[0]["details"] if indicators else None,
        "projections2050": {"models": CLIMATE_MODELS, "ensemble": ensemble, "perModel": projections},
        "solar": solar[0] if solar else None,
        "airQuality": [a for a in air if a["indexType"] == "atmo"],
        "pollens": [a for a in air if a["indexType"] == "pollen"],
        "caveats": [
            "Réanalyse ERA5 (maille ~10 km) : l’îlot de chaleur urbain et les effets de relief local sont lissés.",
            "sunshine_duration ERA5 surestime nettement l’ensoleillement mesuré par héliographe : à utiliser en comparaison entre adresses, pas en valeur absolue.",
        ],
        "notCovered": ["Brouillard (pas de climatologie ouverte à l’adresse)", "Masques solaires dus aux bâtiments voisins"],
    }
