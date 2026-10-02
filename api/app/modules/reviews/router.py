from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import Field

from ...schemas import INSEE_PATTERN, AddressId, CollectQuery, InseeCode, PaginationQuery, StrictModel
from ..geo import service as geo
from ..listings.router import ingest_token
from . import service

router = APIRouter(tags=["reviews"])

ReviewSource = Literal["google_places", "meilleursagents"]
ReviewKind = Literal["place", "neighbourhood", "agency"]


class GoogleCollectQuery(CollectQuery):
    radius: int = Field(500, ge=50, le=5000, description="Rayon de recherche des lieux, en mètres")


class ImportedReview(StrictModel):
    subject: str = Field(min_length=1, max_length=255, description="Nom du quartier ou de l’agence", examples=["Saint-Leu"])
    rating: float | None = Field(None, ge=0, le=5)
    text: str | None = Field(None, max_length=20000)
    author: str | None = Field(None, max_length=120)
    date: str | None = Field(None, description="Date de l’avis (AAAA-MM-JJ ou JJ/MM/AAAA)", examples=["2026-05-14"])
    city: str | None = Field(None, max_length=120)
    postalCode: str | None = Field(None, pattern=r"^\d{5}$")
    inseeCode: str | None = Field(None, pattern=INSEE_PATTERN)
    url: str | None = Field(None, max_length=1000)
    externalId: str | None = Field(None, max_length=120, description="Identifiant stable de l’avis, s’il existe dans le fichier")


class ImportBatch(StrictModel):
    source: Literal["meilleursagents"] = "meilleursagents"
    kind: Literal["neighbourhood", "agency"]
    items: list[ImportedReview] = Field(min_length=1, max_length=2000)


class ReviewQuery(PaginationQuery):
    source: ReviewSource | None = None
    kind: ReviewKind | None = None
    insee: str | None = Field(None, pattern=INSEE_PATTERN)
    postalCode: str | None = Field(None, pattern=r"^\d{5}$")
    minRating: float | None = Field(None, ge=0, le=5)
    q: str | None = Field(None, min_length=2, max_length=80, description="Texte recherché dans l’avis")


@router.post("/addresses/{id}/reviews/collect", status_code=201, summary="Collecte les avis Google des lieux autour de l’adresse (clé GOOGLE_MAPS_API_KEY)")
async def collect_google(id: AddressId, q: Annotated[GoogleCollectQuery, Query()]):
    return await service.collect_google(await geo.get_address(id), q.radius, q.force)


@router.post(
    "/reviews/import",
    status_code=201,
    dependencies=[Depends(ingest_token)],
    summary="Import d’avis de quartiers ou d’agences exportés à la main (MeilleursAgents), 2 000 max par appel",
)
async def import_reviews(dto: ImportBatch):
    return await service.import_reviews(dto.source, dto.kind, [i.model_dump(exclude_none=True) for i in dto.items])


@router.get("/reviews", summary="Avis, paginés et filtrables (source, type, commune, note minimale, texte)")
async def search(q: Annotated[ReviewQuery, Query()]):
    return await service.search(q)


@router.get("/communes/{insee}/reviews/summary", summary="Nombre d’avis et note moyenne de la commune, par source et par type")
async def summary(insee: InseeCode):
    return await service.summary(insee)
