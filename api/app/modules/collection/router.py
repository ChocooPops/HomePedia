from typing import Annotated

from fastapi import APIRouter, Query

from ...schemas import AddressId, ModulesQuery
from ..geo.router import CreateAddress, save_address
from . import service

router = APIRouter(prefix="/addresses", tags=["collection"])


@router.post("/collect", status_code=201, summary="Géocode une adresse puis lance la collecte de tous les modules (one-shot)")
async def geocode_and_collect(dto: CreateAddress, q: Annotated[ModulesQuery, Query()]):
    modules = service.parse_modules(q.modules)
    saved = await save_address(dto, q.force)
    return await service.collect_all(saved["address"]["id"], modules, q.force)


@router.post("/{id}/collect", status_code=201, summary="Collecte tous les modules (ou une sélection) pour une adresse enregistrée")
async def collect(id: AddressId, q: Annotated[ModulesQuery, Query()]):
    return await service.collect_all(id, service.parse_modules(q.modules), q.force)


@router.get("/{id}/report", summary="Rapport consolidé de l’adresse (lecture des données stockées, sans appel externe)")
async def report(id: AddressId):
    return await service.report(id)
