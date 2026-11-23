"""URLs de recherche SeLoger : https://www.seloger.com/classified-search?…"""

from urllib.parse import urlencode

from app.modules.annonces.models import PropertyType, SearchCriteria, SortOrder, TransactionType, ZoneLevel
from app.modules.annonces.sources.base import InvalidCriteria

BASE_URL = "https://www.seloger.com/classified-search"

# SeLoger n'utilise pas les codes INSEE mais ses propres identifiants de lieu, préfixés par le niveau.
FRANCE_PLACE_ID = "AD02FR1"
PLACE_PREFIXES = {
    ZoneLevel.REGION: "AD04",  # AD04FR31 = Auvergne-Rhône-Alpes
    ZoneLevel.DEPARTEMENT: "AD06",  # AD06FR70 = Rhône
    ZoneLevel.COMMUNE: "AD08",  # AD08FR28808 = Lyon
}

DISTRIBUTION_TYPES = {TransactionType.LOCATION: "Rent", TransactionType.VENTE: "Buy"}
ESTATE_TYPES = {PropertyType.MAISON: "House", PropertyType.APPARTEMENT: "Apartment"}
# « tendance » est le tri par défaut du site (aucun paramètre).
# « DateDesc » pour les plus récentes : valeur à confirmer sur une page réelle.
ORDERS = {SortOrder.TENDANCE: None, SortOrder.RECENTES: "DateDesc"}


def build_search_url(criteria: SearchCriteria, page: int = 1) -> str:
    params = {
        "distributionTypes": DISTRIBUTION_TYPES[criteria.transaction],
        "estateTypes": ",".join(_estate_type(t) for t in criteria.property_types),
        "locations": _place_id(criteria),
    }
    if order := ORDERS[criteria.sort]:
        params["order"] = order
    if page > 1:
        params["page"] = page
    return f"{BASE_URL}?{urlencode(params, safe=',')}"


def _estate_type(property_type: PropertyType) -> str:
    if property_type not in ESTATE_TYPES:
        raise InvalidCriteria(f"Type de bien non géré par SeLoger : {property_type}")
    return ESTATE_TYPES[property_type]


def _place_id(criteria: SearchCriteria) -> str:
    zone = criteria.zone
    if zone.level == ZoneLevel.FRANCE:
        return FRANCE_PLACE_ID
    if not zone.place_id and zone.code and zone.level == ZoneLevel.DEPARTEMENT:
        return department_place_id(zone.code)
    prefix = PLACE_PREFIXES[zone.level]
    place_id = (zone.place_id or "").strip().upper()
    if not place_id.startswith(prefix):
        raise InvalidCriteria(
            f"Pour le niveau « {zone.level} », SeLoger attend un identifiant de lieu {prefix}… "
            f"(ex. {prefix}FR…) ; reçu : {zone.place_id!r}"
        )
    return place_id


# Départements métropolitains dans l'ordre des codes, la Corse (2A, 2B) à la place de l'ancien 20.
_DEPARTMENTS = [f"{n:02d}" for n in range(1, 20)] + ["2A", "2B"] + [str(n) for n in range(21, 96)]


def department_place_id(code: str) -> str:
    """Identifiant SeLoger d'un département : son rang dans cette liste (Rhône 69 → AD06FR70, Paris 75 → AD06FR76).

    Les régions et les communes n'ont pas de correspondance calculable : il faut alors un place_id.
    """
    code = code.strip().upper()
    if code not in _DEPARTMENTS:
        raise InvalidCriteria(f"Département {code} : identifiant SeLoger inconnu (seule la métropole est gérée)")
    return f"{PLACE_PREFIXES[ZoneLevel.DEPARTEMENT]}FR{_DEPARTMENTS.index(code) + 1}"
