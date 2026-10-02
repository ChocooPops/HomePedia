from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import Field

from ...schemas import AddressId, CollectQuery, InseeCode, StrictModel
from ..geo import service as geo
from . import service
from .clients import WATER_PARAMETERS

router = APIRouter(tags=["water"])


class ParameterQuery(StrictModel):
    parameter: Literal[tuple(WATER_PARAMETERS)] = Field(description="Code SANDRE du paramètre", examples=["1340"])


@router.post(
    "/addresses/{id}/water/collect",
    status_code=201,
    summary="Collecte qualité de l’eau (Hub’Eau), nappes, restrictions sécheresse (VigiEau)",
)
async def collect(id: AddressId, q: Annotated[CollectQuery, Query()]):
    return await service.collect(await geo.get_address(id), q.force)


@router.get("/addresses/{id}/water", summary="Dernières analyses (nitrates, pesticides, PFAS, dureté), sécheresse, nappes")
async def read(id: AddressId):
    return await service.read(await geo.get_address(id))


@router.get("/communes/{insee}/water-quality", summary="Historique d’un paramètre de qualité de l’eau dans la commune")
async def history(insee: InseeCode, q: Annotated[ParameterQuery, Query()]):
    return await service.history(insee, q.parameter)
