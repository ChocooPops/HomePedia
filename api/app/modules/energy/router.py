from typing import Annotated

from fastapi import APIRouter, Query

from ...schemas import AddressId, CollectQuery, InseeCode
from ..geo import service as geo
from . import ore, service

router = APIRouter(tags=["energy"])


@router.post(
    "/addresses/{id}/energy/collect",
    status_code=201,
    summary="Collecte réseau de chaleur (FCU), desserte gaz (GRDF), consommation électrique (Enedis)",
)
async def collect(id: AddressId, q: Annotated[CollectQuery, Query()]):
    return await service.collect(await geo.get_address(id), q.force)


@router.get("/addresses/{id}/energy", summary="Réseaux disponibles et consommation électrique résidentielle")
async def read(id: AddressId):
    return await service.read(await geo.get_address(id))


@router.post("/communes/{insee}/energy/collect", status_code=201, summary="Collecte la consommation d’électricité et de gaz de la commune (Agence ORE)")
async def collect_commune(insee: InseeCode, q: Annotated[CollectQuery, Query()]):
    return await ore.collect_commune(insee, q.force)


@router.get("/communes/{insee}/energy", summary="Consommation d’électricité et de gaz de la commune, par année et par secteur")
async def read_commune(insee: InseeCode):
    return await ore.read_commune(insee)
