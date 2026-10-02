"""
Orchestration : lance la collecte de tous les modules pour une adresse.
Les modules tournent en parallèle (chaque source garde sa propre limite de débit) ;
l'échec d'un module n'interrompt pas les autres.
"""

import asyncio
import time

from ...errors import ApiError, BadRequest
from ...parse import utcnow
from ..building import service as building
from ..climate import service as climate
from ..connectivity import service as connectivity
from ..energy import service as energy
from ..geo import service as geo
from ..geo import urbanism
from ..mobility import service as mobility
from ..nuisance import service as nuisance
from ..risk import service as risk
from ..services import service as services
from ..socio import service as socio
from ..water import service as water

MODULES = ("geo", "building", "risk", "water", "climate", "nuisance", "energy", "services", "socio", "mobility", "connectivity")


def parse_modules(raw: str | None) -> list[str]:
    if not raw:
        return list(MODULES)
    asked = [m.strip() for m in raw.split(",") if m.strip()]
    unknown = [m for m in asked if m not in MODULES]
    if unknown:
        raise BadRequest(f"Modules inconnus : {', '.join(unknown)} (attendus : {', '.join(MODULES)})")
    return asked


async def _collect_geo(address: dict, force: bool) -> list[dict]:
    outcomes = await asyncio.gather(geo.collect_parcel(address, force), geo.ensure_commune(address["inseeCode"], force))
    return [*outcomes, *await urbanism.collect(address, force)]


def _runner(name: str, address: dict, force: bool):
    if name == "geo":
        return _collect_geo(address, force)
    if name == "socio":
        return socio.collect(address["inseeCode"], force)
    module = {
        "building": building, "risk": risk, "water": water, "climate": climate, "nuisance": nuisance,
        "energy": energy, "services": services, "mobility": mobility, "connectivity": connectivity,
    }[name]
    return module.collect(address, force)


def _message(err: Exception) -> str:
    return str(err.message) if isinstance(err, ApiError) else (str(err) or type(err).__name__)


async def collect_all(address_id: int, modules: list[str], force: bool = False) -> dict:
    started = time.monotonic()
    address = await geo.get_address(address_id)
    reports: list[dict] = []

    async def run(name: str):
        t0 = time.monotonic()
        report = {"module": name, "durationMs": 0, "outcomes": []}
        try:
            report["outcomes"] = await _runner(name, address, force)
        except Exception as err:  # noqa: BLE001 - l'échec d'un module n'interrompt pas les autres
            report["error"] = _message(err)
        report["durationMs"] = int((time.monotonic() - t0) * 1000)
        reports.append(report)

    # Le module géo d'abord : la parcelle et le bâtiment servent de clés aux autres modules.
    if "geo" in modules:
        await run("geo")
        address = await geo.get_address(address_id)
    if "building" in modules:
        await run("building")  # renseigne address.rnbId
        address = await geo.get_address(address_id)
    await asyncio.gather(*(run(m) for m in modules if m not in ("geo", "building")))

    statuses = [o["status"] for r in reports for o in r["outcomes"]]
    return {
        "addressId": address_id,
        "durationMs": int((time.monotonic() - started) * 1000),
        "summary": {s: statuses.count(s) for s in ("success", "cached", "skipped", "error")},
        "modules": sorted(reports, key=lambda r: MODULES.index(r["module"])),
    }


async def report(address_id: int) -> dict:
    """Rapport consolidé : lecture seule, à partir de la base."""
    details = await geo.get_address_details(address_id)
    address = await geo.get_address(address_id)
    insee = address["inseeCode"]

    async def safe(reading):
        try:
            return await reading
        except Exception as err:  # noqa: BLE001 - une section en erreur ne masque pas les autres
            return {"error": _message(err)}

    sections = {
        "urbanism": urbanism.read(address),
        "building": building.read(address),
        "risks": risk.read(address),
        "water": water.read(address),
        "climate": climate.read(address),
        "nuisances": nuisance.read(address),
        "energy": energy.read(address),
        "services": services.read(address),
        "socio": socio.read(insee),
        "mobility": mobility.read(address),
        "connectivity": connectivity.read(address),
    }
    results = await asyncio.gather(*(safe(r) for r in sections.values()))
    return {
        "address": details,
        "market": {"priceIndex": await building.price_index(insee)},
        **dict(zip(sections, results, strict=True)),
        "generatedAt": utcnow(),
    }
