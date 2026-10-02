from typing import Annotated

from fastapi import APIRouter, Query

from ...schemas import AddressId, CollectQuery
from ..geo import service as geo
from . import service

router = APIRouter(tags=["climate"])


@router.post(
    "/addresses/{id}/climate/collect",
    status_code=201,
    summary="Collecte climat observé (10 ans), projections 2031-2050, potentiel solaire, air/pollens",
)
async def collect(id: AddressId, q: Annotated[CollectQuery, Query()]):
    return await service.collect(await geo.get_address(id), q.force)


@router.get(
    "/addresses/{id}/climate",
    summary="Gel, nuits tropicales, neige, vent, ensoleillement, projections, solaire, qualité de l’air",
)
async def read(id: AddressId):
    return await service.read(await geo.get_address(id))
