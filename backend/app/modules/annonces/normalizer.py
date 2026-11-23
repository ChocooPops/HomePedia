"""Conversion d'une annonce brute (RawListing, propre à un site) vers le modèle commun (Listing).

Commun à tous les sites : interprète les libellés usuels des annonces françaises
(« 1 940 € », « 3 pièces », « 2ème étage », « RDC », « Appartement à louer »…).
"""

import re
import unicodedata
from decimal import Decimal, InvalidOperation

from app.modules.annonces.models import Listing, PropertyType, RawListing, SearchCriteria, TransactionType

_TRANSACTIONS = {
    "location": TransactionType.LOCATION,
    "louer": TransactionType.LOCATION,
    "rent": TransactionType.LOCATION,
    "vente": TransactionType.VENTE,
    "vendre": TransactionType.VENTE,
    "achat": TransactionType.VENTE,
    "acheter": TransactionType.VENTE,
    "buy": TransactionType.VENTE,
    "sale": TransactionType.VENTE,
}
_PROPERTY_TYPES = {
    "appartement": PropertyType.APPARTEMENT,
    "apartment": PropertyType.APPARTEMENT,
    "studio": PropertyType.APPARTEMENT,
    "duplex": PropertyType.APPARTEMENT,
    "loft": PropertyType.APPARTEMENT,
    "maison": PropertyType.MAISON,
    "house": PropertyType.MAISON,
    "villa": PropertyType.MAISON,
}

_STREET_TYPES = (
    r"rue|avenue|av|boulevard|bd|cours|place|impasse|all[ée]e|chemin|quai|route|passage|square|"
    r"mont[ée]e|voie|cit[ée]|rond-point|esplanade|promenade|faubourg|parvis|ruelle|sentier|traverse"
)
# « 49 Rue Joliot Curie-Lyon-69005 », « 27 bis cours d'Herbouville LYON 69004 », « 33, Rue Louis Pasteur, 69007 »
_ADDRESS_RE = re.compile(
    rf"(?<![\w.,/])(\d{{1,4}}(?:\s*(?:bis|ter|quater)\b)?)\s*,?\s+"
    rf"((?:{_STREET_TYPES})\b\.?\s+(?!(?:de\s+)?(?:parking|stationnement|garage)\b)[^\n,;:()|]{{2,60}}?)"
    rf"(?=\s*(?:[,;:()|\n.]|\s[-–]\s|\d{{5}}|$))",
    re.IGNORECASE,
)
_ARTICLES = {"de", "du", "des", "d", "la", "le", "les", "l"}
# Mots qui terminent le nom de voie dans une phrase : « 4 rue Magnin à Lyon », « 99 avenue Mermoz dans la commune… ».
_STREET_END_RE = re.compile(
    r"\s+(?:à|dans|un|une|avec|proche|angle|en|pour|entre|près|quartier|situ[ée]e?s?|idéalement|qui|est|"
    r"compos[ée]e?|comprenant)\b.*$",
    re.IGNORECASE,
)


def normalize(raw: RawListing, source: str, criteria: SearchCriteria) -> Listing:
    street_number, street = raw.street_number, raw.street
    if not street:
        street_number, street = extract_street(raw.text, raw.city)

    return Listing(
        source=source,
        source_id=str(raw.source_id),
        url=raw.url,
        # À défaut d'information dans l'annonce, la recherche elle-même fait foi.
        transaction_type=_lookup(raw.transaction, _TRANSACTIONS) or criteria.transaction,
        property_type=_lookup(raw.property_type, _PROPERTY_TYPES)
        or (criteria.property_types[0] if len(criteria.property_types) == 1 else PropertyType.AUTRE),
        price=_decimal(raw.price),
        rooms=_small_int(raw.rooms),
        bedrooms=_small_int(raw.bedrooms),
        surface_m2=_decimal(raw.surface),
        floor=parse_floor(raw.floor),
        floor_label=raw.floor.strip()[:30] if raw.floor else None,
        energy_class=_energy_class(raw.energy_class),
        street_number=street_number,
        street=street,
        postal_code=_postal_code(raw.postal_code),
        city=raw.city.strip() if raw.city else None,
        image_url=raw.image_url,
    )


def parse_floor(label: str | None) -> int | None:
    """« RDC » → 0, « 1er étage » → 1, « 2ème étage » → 2, « Étage 2/4 » → 2."""
    if not label:
        return None
    text = _plain(label)
    if "rdc" in text or "rez" in text:
        return 0
    match = re.search(r"etage\s*(-?\d+)", text) or re.search(r"(-?\d+)", text)
    return int(match.group(1)) if match else None


def extract_street(text: str | None, city: str | None = None) -> tuple[str | None, str | None]:
    """Numéro et voie repérés dans un texte libre (au mieux : beaucoup d'annonces n'en donnent pas)."""
    if not text:
        return None, None
    match = _ADDRESS_RE.search(text)
    if not match:
        return None, None
    number = re.sub(r"\s+", " ", match.group(1)).lower()
    street = _STREET_END_RE.sub("", match.group(2)).strip(" -–")
    return number, _strip_city(street, city)


def _strip_city(street: str, city: str | None) -> str:
    """« Rue Joliot Curie-Lyon » → « Rue Joliot Curie », mais « Rue de Lyon » reste intacte."""
    city_word = _plain(city).split(" ")[0] if city else ""
    if not city_word:
        return street
    words = re.split(r"([\s-]+)", street)  # séparateurs conservés
    if len(words) >= 5 and _plain(words[-1]) == city_word:
        previous = _plain(words[-3]).split(" ")[-1].rstrip("'’")
        if previous not in _ARTICLES and not previous.endswith(("d'", "l'")):
            return "".join(words[:-2]).strip(" -")
    return street


def _lookup(label: str | None, vocabulary: dict) -> object | None:
    for word in _plain(label or "").split(" "):
        if word in vocabulary:
            return vocabulary[word]
    return None


def _decimal(value: str | float | None) -> Decimal | None:
    """Nombre arrondi au centime : 483.20000000000005 → 483.20, « 1 940 € » → 1940."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        compact = re.sub(r"[\s  ]", "", value)  # espaces insécables des montants
        match = re.search(r"\d+(?:[.,]\d+)?", compact)
        if not match:
            return None
        value = match.group().replace(",", ".")
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def _small_int(value: str | float | None) -> int | None:
    number = _decimal(value)
    if number is None or not 0 <= number < 1000:
        return None
    return int(number)


def _energy_class(value: str | None) -> str | None:
    value = (value or "").strip().upper()
    return value if len(value) == 1 and "A" <= value <= "G" else None


def _postal_code(value: str | None) -> str | None:
    match = re.search(r"\b\d{5}\b", value or "")
    return match.group() if match else None


def _plain(text: str) -> str:
    """Minuscules, sans accents, espaces simples."""
    text = unicodedata.normalize("NFD", text.lower())
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).split())
