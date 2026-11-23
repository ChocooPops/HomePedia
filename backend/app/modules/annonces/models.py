"""Modèle commun à tous les sites : critères de recherche, annonce brute, annonce normalisée."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel


class TransactionType(StrEnum):
    VENTE = "vente"
    LOCATION = "location"


class PropertyType(StrEnum):
    APPARTEMENT = "appartement"
    MAISON = "maison"
    AUTRE = "autre"


class ZoneLevel(StrEnum):
    FRANCE = "france"
    REGION = "region"
    DEPARTEMENT = "departement"
    COMMUNE = "commune"


class SortOrder(StrEnum):
    RECENTES = "recentes"
    TENDANCE = "tendance"


@dataclass(frozen=True)
class Zone:
    level: ZoneLevel = ZoneLevel.FRANCE
    code: str | None = None  # code INSEE ; chaque site le traduit s'il sait le faire
    place_id: str | None = None  # identifiant du lieu propre au site, prioritaire sur le code INSEE

    @property
    def key(self) -> str:
        """Identifiant de la zone dans le journal des scrapings."""
        return self.code or self.place_id or "FR"


@dataclass(frozen=True)
class SearchCriteria:
    transaction: TransactionType
    property_types: tuple[PropertyType, ...]
    zone: Zone = Zone()
    sort: SortOrder = SortOrder.RECENTES


@dataclass
class RawListing:
    """Annonce telle que lue sur le site : valeurs typées si le site les fournit, sinon libellés.

    Le parser d'un site remplit ce qu'il trouve ; le normaliseur commun convertit ensuite
    les libellés (« 1 940 € », « 2ème étage », « Appartement »…) en valeurs du modèle commun.
    """

    source_id: str
    url: str
    transaction: str | None = None
    property_type: str | None = None
    price: str | float | None = None
    rooms: str | float | None = None
    bedrooms: str | float | None = None
    surface: str | float | None = None
    floor: str | None = None
    energy_class: str | None = None
    street_number: str | None = None
    street: str | None = None
    postal_code: str | None = None
    city: str | None = None
    image_url: str | None = None  # photo principale
    text: str | None = None  # titre et description, où chercher l'adresse si le site ne la structure pas


@dataclass
class ParsedPage:
    listings: list[RawListing]
    total_count: int | None = None  # nombre total d'annonces de la recherche, si le site l'indique


@dataclass
class Listing:
    """Annonce normalisée, prête à être enregistrée."""

    source: str
    source_id: str
    url: str
    transaction_type: TransactionType
    property_type: PropertyType
    price: Decimal | None = None
    rooms: int | None = None
    bedrooms: int | None = None
    surface_m2: Decimal | None = None
    floor: int | None = None
    floor_label: str | None = None
    energy_class: str | None = None
    street_number: str | None = None
    street: str | None = None
    postal_code: str | None = None
    city: str | None = None
    image_url: str | None = None

    @property
    def address(self) -> str | None:
        """Adresse la plus précise disponible, pour le géocodage."""
        street = " ".join(p for p in (self.street_number, self.street) if p)
        locality = " ".join(p for p in (self.postal_code, self.city) if p)
        if not locality:
            return None
        return f"{street} {locality}" if street else locality


# --------------------------------------------------------------------------- #
# Fiche détaillée d'une annonce (page de l'annonce), stockée dans MongoDB
# --------------------------------------------------------------------------- #


class LabeledValue(BaseModel):
    label: str
    value: str


class FeatureGroup(BaseModel):
    title: str
    items: list[str]


class EnergyScale(BaseModel):
    name: str  # « Diagnostic de performance énergétique (DPE) »…
    rating: str | None = None  # A à G
    values: list[LabeledValue] = []


class School(BaseModel):
    name: str
    level: str | None = None  # Primaire, Collège, Lycée…
    distance: str | None = None
    public: bool = True


class Image(BaseModel):
    url: str
    description: str | None = None


class PriceComparison(BaseModel):
    price_per_m2: float | None = None
    low: float | None = None  # prix au m² le plus bas du secteur
    high: float | None = None
    average: float | None = None


class ListingDetail(BaseModel):
    """Informations de la page d'une annonce, communes à tous les sites.

    Seules les caractéristiques du bien sont conservées : rien sur l'annonceur
    (nom, téléphone, adresse), hormis son type (agence ou particulier).
    """

    title: str | None = None  # « Appartement à louer »
    headline: str | None = None  # titre rédigé par l'annonceur
    description: str | None = None
    price: float | None = None
    price_label: str | None = None  # « 817 €/mois »
    price_note: str | None = None  # « charges comprises »
    key_facts: list[str] = []  # « 2 pièces », « 42,15 m² »…
    features: list[FeatureGroup] = []
    energy: list[EnergyScale] = []
    energy_features: list[LabeledValue] = []  # chauffage, état…
    costs: list[LabeledValue] = []  # charges, honoraires, dépôt de garantie…
    price_comparison: PriceComparison | None = None
    city: str | None = None
    postal_code: str | None = None
    district: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    schools: list[School] = []
    images: list[Image] = []
    virtual_tours: list[str] = []
    tags: list[str] = []  # Exclusivité, Visite 3D…
    publisher_type: str | None = None  # agence, particulier
    published_at: datetime | None = None
    updated_at: datetime | None = None
