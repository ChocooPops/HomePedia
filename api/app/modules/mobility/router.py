from typing import Annotated

from fastapi import APIRouter, Query

from ...schemas import AddressId, CollectQuery
from ..geo import service as geo
from . import service

router = APIRouter(tags=["mobility"])


@router.post(
    "/addresses/{id}/mobility/collect",
    status_code=201,
    summary="Collecte bornes IRVE, parkings, arrêts de transport, aménagements cyclables, flux GTFS",
)
async def collect(id: AddressId, q: Annotated[CollectQuery, Query()]):
    return await service.collect(await geo.get_address(id), q.force)


@router.get("/addresses/{id}/mobility", summary="Arrêts à moins de 800 m, bornes de recharge, parkings, pistes cyclables")
async def read(id: AddressId):
    return await service.read(await geo.get_address(id))
