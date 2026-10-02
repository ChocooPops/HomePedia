"""Énergie : réseau de chaleur (FCU), desserte gaz (GRDF), consommation électrique résidentielle (Enedis)."""

import asyncio

from ...collector import collector
from ...db import db
from ..geo.service import point_of
from . import clients, ore
from .normalizers import (
    COMMUNE_KEY,
    enedis_address_key,
    normalize_consumption,
    normalize_gas_network,
    normalize_heat_network,
)


async def collect(address: dict, force: bool = False) -> list[dict]:
    p = point_of(address)
    insee = address["inseeCode"]
    target = f"address:{address['id']}"

    async def heat_task(stamp: dict) -> dict:
        res = await clients.fcu_eligibility(p)
        await db.upsert("energy_network_access", normalize_heat_network(res, address["id"], stamp))
        return {"items": 1, "raw": res}

    async def gas_task(stamp: dict) -> dict:
        rows = await clients.grdf_network(insee)
        await db.upsert("energy_network_access", normalize_gas_network(rows, address["id"], stamp))
        return {"items": len(rows)}

    async def electricity_task(stamp: dict) -> dict:
        key = enedis_address_key(address["housenumber"], address["street"])
        rows = await clients.enedis_by_address(insee, key) if key else []
        address_key = key if key is not None else COMMUNE_KEY
        if not rows:
            # Pas de ligne pour l'adresse (moins de 10 logements, secret statistique) : moyenne communale.
            rows = await clients.enedis_latest_of_commune(insee)
            address_key = COMMUNE_KEY
        values = [normalize_consumption(r, insee, address_key, stamp) for r in rows]
        if values:
            await db.upsert("electricity_consumption", values)
        return {"items": len(values)}

    return list(await asyncio.gather(
        collector.run("fcu", target, heat_task, force=force),
        collector.run("grdf", target, gas_task, force=force),
        collector.run("enedis", target, electricity_task, force=force),
        ore.collect_commune(insee, force),
    ))


async def read(address: dict) -> dict:
    key = enedis_address_key(address["housenumber"], address["street"])
    networks, consumption, commune = await asyncio.gather(
        db.find("energy_network_access", {"addressId": address["id"]}),
        db.find(
            "electricity_consumption",
            {"inseeCode": address["inseeCode"], "addressKey": [key if key is not None else COMMUNE_KEY, COMMUNE_KEY]},
            order="t.year DESC",
        ),
        ore.read_commune(address["inseeCode"]),
    )
    return {
        "heatNetwork": next((n for n in networks if n["networkType"] == "heat"), None),
        "gasNetwork": next((n for n in networks if n["networkType"] == "gas"), None),
        "electricity": {
            "atAddress": [c for c in consumption if c["addressKey"] != COMMUNE_KEY],
            "communeAverage": [c for c in consumption if c["addressKey"] == COMMUNE_KEY],
        },
        # Électricité et gaz de la commune, tous secteurs (Agence ORE).
        "commune": {"latestYear": commune["latestYear"], "latest": commune["latest"], "totalsByYear": commune["totalsByYear"]},
        "notCovered": ["Historique des coupures électriques à l’adresse"],
    }
