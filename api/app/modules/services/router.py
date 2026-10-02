from typing import Annotated

from fastapi import APIRouter, Query

from ...schemas import AddressId, CollectQuery, RadiusQuery
from ..geo import service as geo
from . import service

router = APIRouter(tags=["services"])


@router.post(
    "/addresses/{id}/services/collect",
    status_code=201,
    summary="Collecte santé, commerces, crèches, écoles (IPS, effectifs) et temps de trajet IGN",
)
async def collect(id: AddressId, q: Annotated[CollectQuery, Query()]):
    return await service.collect(await geo.get_address(id), q.force)


@router.get("/addresses/{id}/services", summary="Services par catégorie, urgences, boulangeries ouvertes le dimanche, temps de trajet")
async def read(id: AddressId):
    return await service.read(await geo.get_address(id))


@router.get("/addresses/{id}/schools", summary="Écoles, collèges, lycées à proximité avec IPS et taille moyenne des classes")
async def schools(id: AddressId, q: Annotated[RadiusQuery, Query()]):
    return await service.schools_around(await geo.get_address(id), q.radius if q.radius is not None else 1500)
