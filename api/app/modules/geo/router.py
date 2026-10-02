from typing import Annotated

from fastapi import APIRouter, Path, Query
from pydantic import Field, model_validator

from ...schemas import (
    DEPARTMENT_PATTERN,
    INSEE_PATTERN,
    AddressId,
    CollectQuery,
    InseeCode,
    PaginationQuery,
    RadiusQuery,
    StrictModel,
)
from . import service, urbanism

router = APIRouter(tags=["geo"])


class CreateAddress(StrictModel):
    q: str | None = Field(None, min_length=3, description="Adresse en texte libre (ou lat/lon)", examples=["2 rue de la République, Amiens"])
    lat: float | None = Field(None, ge=-90, le=90, examples=[49.892808])
    lon: float | None = Field(None, ge=-180, le=180, examples=[2.297087])

    @model_validator(mode="after")
    def _text_or_point(self):
        if not self.q and (self.lat is None or self.lon is None):
            raise ValueError("renseigner q (adresse en texte) ou lat et lon")
        return self


class SearchQuery(StrictModel):
    q: str = Field(min_length=3)
    limit: int = Field(5, ge=1, le=20)


class AddressListQuery(PaginationQuery):
    insee: str | None = Field(None, pattern=INSEE_PATTERN, examples=["80021"])


class CommuneListQuery(PaginationQuery):
    department: str | None = Field(None, pattern=DEPARTMENT_PATTERN, examples=["80"])
    region: str | None = Field(None, pattern=r"^\d{2}$", examples=["32"])


Idu = Annotated[str, Path(pattern=r"^[0-9AB]{5}[0-9]{3}[0-9A-Z]{2}[0-9]{4}$", description="Identifiant de parcelle à 14 caractères")]
Department = Annotated[str, Path(pattern=DEPARTMENT_PATTERN)]


async def save_address(dto: CreateAddress, force: bool) -> dict:
    """Géocode (texte ou point) et enregistre : { address, outcomes }."""
    if dto.q:
        return await service.geocode_and_save(dto.q, force)
    return await service.reverse_and_save({"lat": dto.lat, "lon": dto.lon}, force)


@router.get("/geo/search", summary="Autocomplétion BAN (sans enregistrement)")
async def search(q: Annotated[SearchQuery, Query()]):
    return await service.search(q.q, q.limit)


@router.post("/addresses", status_code=201, summary="Géocode (texte ou lat/lon) et enregistre une adresse + sa commune + sa parcelle")
async def create(dto: CreateAddress, q: Annotated[CollectQuery, Query()]):
    return await save_address(dto, q.force)


@router.get("/addresses", summary="Liste des adresses enregistrées")
async def list_addresses(q: Annotated[AddressListQuery, Query()]):
    items, total = await service.list_addresses(q.insee, q.limit, q.offset)
    return {"total": total, "page": q.page, "limit": q.limit, "items": items}


@router.get("/addresses/{id}", summary="Adresse avec sa commune et sa parcelle (géométrie GeoJSON)")
async def get(id: AddressId):
    return await service.get_address_details(id)


@router.delete("/addresses/{id}", status_code=204, summary="Supprime une adresse et les données qui lui sont rattachées")
async def remove(id: AddressId):
    await service.delete_address(id)


@router.get("/addresses/{id}/indicators", summary="Indicateurs calculés à l’adresse (tous domaines)")
async def indicators(id: AddressId):
    return await service.indicators_of(id)


@router.post("/addresses/{id}/urbanism/collect", status_code=201, summary="Collecte PLU (zones, prescriptions), servitudes (AC1) et monuments historiques")
async def collect_urbanism(id: AddressId, q: Annotated[CollectQuery, Query()]):
    return await urbanism.collect(await service.get_address(id), q.force)


@router.get("/addresses/{id}/urbanism", summary="Zonage PLU au point et alentours, emplacements réservés, périmètres MH")
async def read_urbanism(id: AddressId, q: Annotated[RadiusQuery, Query()]):
    return await urbanism.read(await service.get_address(id), q.radius or 250)


@router.get("/communes", summary="Communes enregistrées (filtre département / région)")
async def communes(q: Annotated[CommuneListQuery, Query()]):
    items, total = await service.list_communes(q.department, q.region, q.limit, q.offset)
    return {"total": total, "page": q.page, "limit": q.limit, "items": items}


@router.get("/communes/{insee}", summary="Commune (collectée à la volée si absente)")
async def commune(insee: InseeCode):
    return await service.get_commune(insee)


@router.post("/communes/{insee}/collect", status_code=201, summary="Recharge une commune depuis l’API Géo")
async def collect_commune(insee: InseeCode, q: Annotated[CollectQuery, Query()]):
    return await service.ensure_commune(insee, q.force)


@router.post("/departments/{dep}/communes/collect", status_code=201, summary="Importe toutes les communes d’un département")
async def collect_department(dep: Department, q: Annotated[CollectQuery, Query()]):
    return await service.collect_department_communes(dep, q.force)


@router.get("/parcels/{idu}", summary="Parcelle cadastrale (collectée à la volée si absente)")
async def parcel(idu: Idu, q: Annotated[CollectQuery, Query()]):
    return await service.get_parcel(idu, q.force)
