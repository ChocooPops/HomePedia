"""Lecture d'une page de résultats SeLoger.

1. Source principale : l'état JSON que la page embarque pour le navigateur,
   window["__UFRN_FETCHER__"] = JSON.parse("…"), qui contient les annonces structurées.
2. Secours : les cartes HTML (attributs data-testid), si cet état est absent ou a changé de forme.

Seules les caractéristiques du bien sont lues : rien sur l'annonceur ni ses coordonnées.
"""

import json
import logging
import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from app.modules.annonces.models import ParsedPage, RawListing
from app.modules.annonces.sources.base import ParseError

logger = logging.getLogger(__name__)

_STATE_RE = re.compile(r'window\["__UFRN_FETCHER__"\]\s*=\s*JSON\.parse\(("(?:[^"\\]|\\.)*")\)', re.S)
_POSTAL_CODE_RE = re.compile(r"\((\d{5})\)")


def parse(html: str) -> ParsedPage:
    serp = _search_state(html)
    if serp is not None:
        try:
            return _from_state(serp)
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            logger.warning("État JSON SeLoger inattendu (%r) : lecture des cartes HTML", exc)
    return _from_cards(html)


# --------------------------------------------------------------------------- #
# État JSON
# --------------------------------------------------------------------------- #


def _search_state(html: str) -> dict[str, Any] | None:
    match = _STATE_RE.search(html)
    if not match:
        return None
    try:
        # Chaîne JavaScript (JSON une première fois) contenant elle-même du JSON.
        state = json.loads(json.loads(match.group(1)))
    except json.JSONDecodeError:
        return None
    return (state.get("data") or state).get("classified-serp-data")


def _from_state(serp: dict[str, Any]) -> ParsedPage:
    by_id = serp["classifiedsData"]
    # « classifieds » donne l'ordre des résultats ; classifiedsData contient aussi des suggestions hors recherche.
    ids = [i if isinstance(i, str) else i.get("id") for i in serp.get("classifieds") or by_id]
    listings = [_from_classified(by_id[i]) for i in ids if i in by_id]
    return ParsedPage(listings=listings, total_count=serp.get("totalCount"))


def _from_classified(c: dict[str, Any]) -> RawListing:
    raw = c.get("rawData") or {}
    facts = {f.get("type"): f for f in (c.get("hardFacts") or {}).get("facts", [])}
    address = (c.get("location") or {}).get("address") or {}
    description = c.get("mainDescription") or {}
    price = (c.get("hardFacts") or {}).get("price") or {}

    def fact(name: str) -> str | None:
        return (facts.get(name) or {}).get("value")

    return RawListing(
        source_id=c["id"],
        url=c["url"],
        transaction=raw.get("distributionType"),  # RENT, BUY
        property_type=raw.get("propertyType") or raw.get("propertyTypeLabel"),  # APARTMENT, HOUSE
        price=_first(raw.get("price"), (c.get("tracking") or {}).get("price"), price.get("value")),
        rooms=_first(raw.get("nbroom"), fact("numberOfRooms")),
        bedrooms=_first(raw.get("nbbedroom"), fact("numberOfBedrooms")),
        surface=_first((raw.get("surface") or {}).get("main"), fact("livingSpace")),
        floor=fact("numberOfFloors"),
        energy_class=_first(c.get("energyClass"), (c.get("tracking") or {}).get("energy_certificate")),
        street_number=_first(address.get("houseNumber"), address.get("streetNumber")),
        street=address.get("street"),
        postal_code=address.get("zipCode"),
        city=address.get("city"),
        image_url=_first_image(c),
        text="\n".join(t for t in (description.get("headline"), description.get("description")) if t),
    )


def _first_image(c: dict[str, Any]) -> str | None:
    images = (c.get("gallery") or {}).get("images") or []
    return next((img["url"] for img in images if img.get("url")), None)


def _first(*values: Any) -> Any:
    return next((v for v in values if v not in (None, "")), None)


# --------------------------------------------------------------------------- #
# Cartes HTML (secours)
# --------------------------------------------------------------------------- #


def _from_cards(html: str) -> ParsedPage:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select('[data-testid="serp-core-classified-card-testid"]')
    if not cards:
        raise ParseError("Aucune annonce trouvée dans la page SeLoger (blocage ou format modifié)")
    return ParsedPage(listings=[listing for card in cards if (listing := _from_card(card))])


def _from_card(card: Tag) -> RawListing | None:
    link = card.select_one('[data-testid="card-mfe-covering-link-testid"]')
    if link is None or not link.get("href"):
        return None
    url = str(link["href"])

    keyfacts = _text(card, "cardmfe-keyfacts-testid", sep="|")
    facts = [f.strip() for f in (keyfacts or "").split("|") if f.strip() not in ("", "·")]
    rooms = next((f for f in facts if "pièce" in f), None)
    bedrooms = next((f for f in facts if "chambre" in f), None)
    surface = next((f for f in facts if "m²" in f), None)
    floor = next((f for f in facts if "étage" in f.lower() or f.upper() == "RDC"), None)

    # « Champvert, Lyon 5ème arrondissement (69005) »
    address = _text(card, "cardmfe-description-box-address", sep=" ") or ""
    postal = _POSTAL_CODE_RE.search(address)
    locality = _POSTAL_CODE_RE.sub("", address).strip()

    # « 990 € | Appartement à louer | 2 pièces… » : le titre suit le prix.
    description = _text(card, "cardmfe-description-box-text-test-id", sep="|") or ""
    title = next((p.strip() for p in description.split("|")[1:2]), "")

    return RawListing(
        source_id=url.rstrip("/").rsplit("/", 1)[-1],
        url=url,
        transaction=_transaction_from_url(url),
        property_type=title.split(" ")[0] if title else None,
        price=_text(card, "cardmfe-price-testid"),
        rooms=rooms,
        bedrooms=bedrooms,
        surface=surface,
        floor=floor,
        energy_class=_text(card, "card-mfe-energy-performance-class"),
        postal_code=postal.group(1) if postal else None,
        city=locality.rsplit(",", 1)[-1].strip() or None,
        # Galerie seulement : la première image de la carte est le logo de l'agence.
        image_url=(card.select_one('[data-testid="card-mfe-picture-box-gallery-test-id"] img[src]') or {}).get("src"),
        text=title,
    )


def _text(card: Tag, testid: str, sep: str = "") -> str | None:
    element = card.select_one(f'[data-testid="{testid}"]')
    return element.get_text(sep, strip=True) if element else None


def _transaction_from_url(url: str) -> str | None:
    # https://www.seloger.com/annonce/location/… ou /annonce/achat/…
    match = re.search(r"/annonce/([^/]+)/", url)
    return match.group(1) if match else None
