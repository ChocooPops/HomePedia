from typing import Annotated

from fastapi import APIRouter, Query

from ...schemas import CollectQuery, InseeCode
from . import service

router = APIRouter(prefix="/communes/{insee}/socio", tags=["socio"])


@router.post("/collect", status_code=201, summary="Collecte recensement (Melodi), fiscalité locale (DGFiP), délinquance (SSMSI)")
async def collect(insee: InseeCode, q: Annotated[CollectQuery, Query()]):
    return await service.collect(insee, q.force)


@router.get("", summary="Âge, résidences secondaires, vacance, ancienneté, taxe foncière, délinquance")
async def read(insee: InseeCode):
    return await service.read(insee)
