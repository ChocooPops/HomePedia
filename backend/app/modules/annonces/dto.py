from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.modules.annonces.models import ListingDetail, PropertyType, SortOrder, TransactionType, ZoneLevel


class ZoneDto(BaseModel):
    level: ZoneLevel = ZoneLevel.FRANCE
    code: str | None = Field(
        None, description="Code INSEE, si le site sait le traduire (SeLoger : départements seulement)", examples=["69"]
    )
    place_id: str | None = Field(
        None,
        description="Identifiant du lieu sur le site (SeLoger : AD04… région, AD06… département, AD08… commune). "
        "Inutile pour la France.",
        examples=["AD08FR28808"],
    )


class ScrapeRequestDto(BaseModel):
    source: str = Field("seloger", description="Site à scraper")
    transaction: TransactionType
    property_types: list[Literal[PropertyType.APPARTEMENT, PropertyType.MAISON]] = Field(
        default=[PropertyType.APPARTEMENT, PropertyType.MAISON], min_length=1
    )
    zone: ZoneDto = ZoneDto()
    sort: SortOrder = SortOrder.RECENTES
    pages: int = Field(1, ge=1, le=20, description="Pages de résultats à récupérer (un crédit ScrapeUnblocker chacune)")
    dry_run: bool = Field(False, description="Renvoie seulement les URLs générées, sans rien télécharger")


class ScrapeResultDto(BaseModel):
    source: str
    urls: list[str] = Field(description="Pages de résultats demandées")
    total_count: int | None = Field(None, description="Nombre total d'annonces de la recherche sur le site")
    found: int = Field(0, description="Annonces lues dans les pages")
    inserted: int = 0
    updated: int = 0
    geocoded: int = Field(0, description="Adresses envoyées au géocodeur (les autres étaient déjà en base)")


class AnnonceFiltersDto(BaseModel):
    source: str | None = None
    transaction_type: TransactionType | None = None
    property_type: PropertyType | None = None
    postal_code: str | None = Field(None, pattern=r"^\d{5}$")
    insee_code: str | None = Field(None, description="Code INSEE de la commune (issu du géocodage)")
    min_price: float | None = Field(None, ge=0)
    max_price: float | None = Field(None, ge=0)
    limit: int = Field(50, ge=1, le=500)
    offset: int = Field(0, ge=0)


class AnnonceDto(BaseModel):
    id: int
    source: str
    source_label: str = Field(description="Nom affichable du site d'origine (« SeLoger »)")
    source_id: str
    url: str
    transaction_type: TransactionType
    property_type: PropertyType
    price: float | None
    rooms: int | None
    bedrooms: int | None
    surface_m2: float | None
    floor: int | None = Field(description="0 = rez-de-chaussée")
    floor_label: str | None
    energy_class: str | None
    street_number: str | None
    street: str | None
    postal_code: str | None
    city: str | None
    image_url: str | None = Field(None, description="Photo principale")
    latitude: float | None
    longitude: float | None
    geocoding_score: float | None
    geocoded_address: str | None
    insee_code: str | None
    first_seen_at: datetime
    last_seen_at: datetime


class MapQueryDto(BaseModel):
    """Une commune (`commune_code`), ou à défaut l'emprise de la carte (`west`, `south`, `east`, `north`)."""

    west: float | None = Field(None, ge=-180, le=180)
    south: float | None = Field(None, ge=-90, le=90)
    east: float | None = Field(None, ge=-180, le=180)
    north: float | None = Field(None, ge=-90, le=90)
    commune_code: str | None = Field(
        None,
        pattern=r"^(\d{5}|2[ABab]\d{3})$",
        description="Code INSEE de la commune choisie : ses annonces, quelle que soit l'emprise",
    )
    department_code: str | None = Field(
        None,
        pattern=r"^(\d{2}|2[AB]|97\d)$",
        description="Département au centre de la carte : s'il n'a encore aucune annonce en base, il est scrapé",
    )
    transaction_type: TransactionType = TransactionType.LOCATION
    property_type: PropertyType | None = None
    limit: int = Field(1000, ge=1, le=5000)

    @model_validator(mode="after")
    def _zone_required(self):
        if not self.commune_code and None in (self.west, self.south, self.east, self.north):
            raise ValueError("Indiquer commune_code, ou l'emprise complète (west, south, east, north)")
        return self


class SyncDto(BaseModel):
    """Ce qui a été fait pour le département demandé, pour un site."""

    source: str
    source_label: str
    status: Literal["database", "pending", "scraped", "recently_scraped", "unsupported", "error"] = Field(
        description="database : annonces déjà en base ; pending : site en cours d'interrogation (redemander dans quelques secondes) ; scraped : site interrogé, annonces ajoutées ; recently_scraped : site déjà "
        "interrogé récemment sans résultat ; unsupported : zone non gérée par le site ; error : échec"
    )
    found: int | None = Field(None, description="Annonces récupérées (status scraped)")
    detail: str | None = None


class MapResultDto(BaseModel):
    annonces: list[AnnonceDto]
    truncated: bool = Field(description="Plus d'annonces que `limit` dans la zone")
    sync: list[SyncDto]


class AnnonceDetailDto(ListingDetail):
    """Fiche complète d'une annonce, lue sur sa page puis conservée dans MongoDB."""

    annonce_id: int
    source: str
    source_label: str
    source_id: str
    url: str
    scraped_at: datetime = Field(description="Date de la lecture de la page")
    cached: bool = Field(description="true : fiche déjà en base ; false : page lue à l'instant (un crédit)")
