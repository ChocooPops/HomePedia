from typing import Annotated

from fastapi import APIRouter, Query

from ...schemas import AddressId, CollectQuery
from ..geo import service as geo
from . import service

router = APIRouter(tags=["connectivity"])


@router.post("/connectivity/fixed/import", status_code=201, summary="Importe l’éligibilité fixe par commune (ARCEP, ~35 000 communes)")
async def import_fixed(q: Annotated[CollectQuery, Query()]):
    return await service.import_fixed(q.force)


@router.post(
    "/connectivity/mobile-sites/import",
    status_code=201,
    summary="Importe les sites mobiles 2G/3G/4G/5G par opérateur (ARCEP, ~125 000 sites)",
)
async def import_mobile(q: Annotated[CollectQuery, Query()]):
    return await service.import_mobile_sites(q.force)


@router.post("/addresses/{id}/connectivity/collect", status_code=201, summary="S’assure que les référentiels ARCEP sont chargés")
async def collect(id: AddressId, q: Annotated[CollectQuery, Query()]):
    return await service.collect(await geo.get_address(id), q.force)


@router.get("/addresses/{id}/connectivity", summary="Fibre (taux communal) et proximité des antennes 4G/5G par opérateur")
async def read(id: AddressId):
    return await service.read(await geo.get_address(id))
