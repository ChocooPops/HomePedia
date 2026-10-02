from typing import Annotated

from fastapi import APIRouter, Query

from ...schemas import AddressId, RadiusQuery
from ..geo import service as geo
from . import service

router = APIRouter(tags=["nuisance"])


@router.post(
    "/addresses/{id}/nuisances/collect",
    status_code=201,
    summary="Collecte OSM (bars, lieux de culte, élevages, STEP, lignes HT, éoliennes...), PEB, survols OpenSky",
)
async def collect(id: AddressId, q: Annotated[RadiusQuery, Query()]):
    return await service.collect(await geo.get_address(id), q.force, q.radius if q.radius is not None else 1000)


@router.get("/addresses/{id}/nuisances", summary="Sources de nuisance par catégorie (nombre, plus proche), antennes, survols")
async def read(id: AddressId, q: Annotated[RadiusQuery, Query()]):
    return await service.read(await geo.get_address(id), q.radius if q.radius is not None else 1000)
