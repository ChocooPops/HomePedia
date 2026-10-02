import re
from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import Field, field_validator

from ...schemas import AddressId, CollectQuery, InseeCode, PaginationQuery, RadiusQuery
from ..geo import service as geo
from . import service

router = APIRouter(tags=["building"])


class DvfCollectQuery(CollectQuery):
    years: str | None = Field(None, description="Années à importer (défaut : toutes)", examples=["2023,2024"])

    @field_validator("years")
    @classmethod
    def _integers(cls, v: str | None) -> str | None:
        # Un entier en tête de chaque élément, sinon rejet.
        if v is not None and not all(re.match(r"\s*[+-]?\d+", part) for part in v.split(",")):
            raise ValueError("each value in years must be an integer number")
        return v

    @property
    def year_list(self) -> list[int] | None:
        if self.years is None:
            return None
        return [int(re.match(r"\s*([+-]?\d+)", part)[1]) for part in self.years.split(",")]


class DvfListQuery(PaginationQuery):
    year: int | None = Field(None, ge=2014, le=2100, examples=[2024])
    type: Literal["Maison", "Appartement", "Dépendance", "Local industriel. commercial ou assimilé"] | None = None


@router.post(
    "/addresses/{id}/building/collect", status_code=201,
    summary="Collecte RNB + BDNB + DPE + copropriété (RNIC) + DVF de la commune",
)
async def collect(id: AddressId, q: Annotated[CollectQuery, Query()]):
    return await service.collect(await geo.get_address(id), q.force)


@router.get("/addresses/{id}/building", summary="Bâtiment, DPE, copropriété et présomptions (plomb, amiante, interdiction de louer)")
async def read(id: AddressId):
    return await service.read(await geo.get_address(id))


@router.get("/addresses/{id}/dvf", summary="Ventes DVF autour de l’adresse")
async def around(id: AddressId, q: Annotated[RadiusQuery, Query()]):
    return await service.mutations_around(await geo.get_address(id), q.radius if q.radius is not None else 500)


@router.post(
    "/communes/{insee}/dvf/collect", status_code=201,
    summary="Importe les ventes DVF d’une commune et recalcule l’indice de prix",
)
async def collect_dvf(insee: InseeCode, q: Annotated[DvfCollectQuery, Query()]):
    return await service.collect_dvf(insee, q.year_list, q.force)


@router.get("/communes/{insee}/dvf", summary="Ventes DVF d’une commune (filtre année / type)")
async def list_dvf(insee: InseeCode, q: Annotated[DvfListQuery, Query()]):
    return await service.list_mutations(insee, q.year, q.type, q.page, q.limit)


@router.get("/communes/{insee}/price-index", summary="Prix au m² (médiane, moyenne, quartiles) par année et type de bien")
async def price_index(insee: InseeCode):
    return await service.price_index(insee)


@router.post(
    "/communes/{insee}/price-index/compute", status_code=201,
    summary="Recalcule l’indice de prix à partir des ventes stockées",
)
async def compute(insee: InseeCode):
    return await service.compute_price_index(insee)
