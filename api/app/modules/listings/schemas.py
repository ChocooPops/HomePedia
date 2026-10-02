from datetime import datetime
from typing import Literal

from pydantic import Field, HttpUrl

from ...schemas import DEPARTMENT_PATTERN, INSEE_PATTERN, PaginationQuery, StrictModel

ListingSource = Literal["seloger", "bienici", "leboncoin"]
TransactionType = Literal["sale", "rent"]
PropertyType = Literal["apartment", "house", "land", "parking", "other"]
ListingSort = Literal["recent", "price", "-price", "priceM2", "-priceM2"]

ENERGY_CLASS_PATTERN = r"^[A-Ga-g]$"
POSTAL_CODE_PATTERN = r"^\d{5}$"


class IngestListing(StrictModel):
    sourceId: str = Field(min_length=1, max_length=64, description="Identifiant de l’annonce sur le site d’origine", examples=["2584413921"])
    url: HttpUrl = Field(examples=["https://www.leboncoin.fr/ad/ventes_immobilieres/2584413921"])
    transactionType: TransactionType
    propertyType: PropertyType
    title: str | None = Field(None, max_length=300)
    description: str | None = Field(None, max_length=20000)
    priceEur: float = Field(ge=0, description="Prix de vente, ou loyer mensuel pour une location", examples=[189000])
    areaM2: float | None = Field(None, ge=0, examples=[64])
    landAreaM2: float | None = Field(None, ge=0)
    rooms: int | None = Field(None, ge=0, examples=[3])
    bedrooms: int | None = Field(None, ge=0, examples=[2])
    floor: int | None = None
    energyClass: str | None = Field(None, pattern=ENERGY_CLASS_PATTERN, description="Étiquette DPE (A à G)", examples=["D"])
    ghgClass: str | None = Field(None, pattern=ENERGY_CLASS_PATTERN, description="Étiquette GES (A à G)", examples=["C"])
    city: str | None = Field(None, max_length=120, examples=["Amiens"])
    postalCode: str | None = Field(None, pattern=POSTAL_CODE_PATTERN, examples=["80000"])
    inseeCode: str | None = Field(None, pattern=INSEE_PATTERN, examples=["80021"])
    lat: float | None = Field(None, ge=-90, le=90, examples=[49.892808])
    lon: float | None = Field(None, ge=-180, le=180, examples=[2.297087])
    photos: list[HttpUrl] | None = Field(None, max_length=50)
    publishedAt: datetime | None = Field(None, examples=["2026-09-28T08:12:00Z"])
    raw: dict | None = Field(None, description="Objet d’origine tel que scrapé, conservé sans transformation")


class IngestBatch(StrictModel):
    source: ListingSource
    items: list[IngestListing] = Field(min_length=1, max_length=500)


class ListingFilter(PaginationQuery):
    source: ListingSource | None = None
    transactionType: TransactionType | None = None
    propertyType: PropertyType | None = None
    minPrice: float | None = Field(None, ge=0)
    maxPrice: float | None = Field(None, ge=0)
    minArea: float | None = Field(None, ge=0)
    maxArea: float | None = Field(None, ge=0)
    minRooms: int | None = Field(None, ge=0, description="Nombre minimal de pièces")


class ListingListQuery(ListingFilter):
    insee: str | None = Field(None, pattern=INSEE_PATTERN, examples=["80021"])
    postalCode: str | None = Field(None, pattern=POSTAL_CODE_PATTERN, examples=["80000"])
    department: str | None = Field(None, pattern=DEPARTMENT_PATTERN, examples=["80"])
    sort: ListingSort = "recent"


class ListingNearQuery(ListingFilter):
    radius: int = Field(1000, ge=50, le=20000, description="Rayon de recherche en mètres")
