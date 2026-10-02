import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query

from ...config import settings
from ...errors import Unauthorized
from ...schemas import AddressId, InseeCode
from ..geo import service as geo
from . import service
from .schemas import IngestBatch, ListingListQuery, ListingNearQuery

router = APIRouter(tags=["listings"])


def ingest_token(x_ingest_token: Annotated[str | None, Header(description="Requis si INGEST_TOKEN est défini")] = None):
    """Protège l'ingestion par l'en-tête X-Ingest-Token quand INGEST_TOKEN est défini (sinon ouvert, usage local)."""
    expected = settings.ingest_token
    if expected and not hmac.compare_digest((x_ingest_token or "").encode(), expected.encode()):
        raise Unauthorized("Jeton d’ingestion absent ou invalide")


@router.post(
    "/listings/ingest",
    status_code=201,
    dependencies=[Depends(ingest_token)],
    summary="Ingestion d’un lot d’annonces scrapées (SeLoger, Bien’ici, Leboncoin), 500 max par appel",
)
async def ingest(dto: IngestBatch):
    return await service.ingest(dto.source, dto.items)


@router.get("/listings", summary="Annonces, paginées et filtrables (commune, département, type, prix, surface, pièces)")
async def search(q: Annotated[ListingListQuery, Query()]):
    return await service.search(q)


@router.get("/listings/{id}", summary="Annonce complète, avec historique de prix et objet d’origine")
async def get(id: str):
    return await service.get(id)


@router.get("/addresses/{id}/listings", summary="Annonces géolocalisées dans un rayon autour de l’adresse, triées par distance")
async def near(id: AddressId, q: Annotated[ListingNearQuery, Query()]):
    return await service.near(geo.point_of(await geo.get_address(id)), q)


@router.get("/communes/{insee}/listings/stats", summary="Prix au m² des annonces de la commune (médiane, moyenne, extrêmes) par type")
async def stats(insee: InseeCode):
    return await service.commune_stats(insee)
