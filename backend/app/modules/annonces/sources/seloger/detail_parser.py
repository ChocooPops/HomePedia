"""Lecture de la page d'une annonce SeLoger (https://www.seloger.com/annonce/…).

1. Source principale : l'état JSON embarqué dans la page,
   window["__UFRN_LIFECYCLE_SERVERREQUEST__"] = JSON.parse("…") → app_cldp.data.classified.
2. Secours : données structurées JSON-LD, balises og:image et blocs HTML (data-testid).

Les coordonnées de l'annonceur (nom, téléphones, adresse, mentions légales) ne sont pas lues.
"""

import json
import logging
import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

from app.modules.annonces.models import (
    EnergyScale,
    FeatureGroup,
    Image,
    LabeledValue,
    ListingDetail,
    PriceComparison,
    School,
)
from app.modules.annonces.sources.base import ParseError

logger = logging.getLogger(__name__)

_STATE_RE = re.compile(
    r'window\["__UFRN_LIFECYCLE_SERVERREQUEST__"\]\s*=\s*JSON\.parse\(("(?:[^"\\]|\\.)*")\)', re.S
)
_NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")

SCHOOL_LEVELS = {"PRIMARY": "Primaire", "MIDDLE": "Collège", "HIGH": "Lycée", "SECONDARY": "Lycée"}
TAGS = {
    "isExclusive": "Exclusivité",
    "has3DVisit": "Visite 3D",
    "isNew": "Nouvelle annonce",
    "hasBrokerageFee": "Frais d'agence",
}


def parse_detail(html: str) -> ListingDetail:
    classified = _classified(html)
    if classified is not None:
        try:
            return _from_state(classified)
        except (KeyError, IndexError, TypeError, AttributeError, ValueError) as exc:
            logger.warning("État JSON SeLoger inattendu (%r) : lecture du HTML", exc)
    return _from_html(html)


# --------------------------------------------------------------------------- #
# État JSON
# --------------------------------------------------------------------------- #


def _classified(html: str) -> dict[str, Any] | None:
    match = _STATE_RE.search(html)
    if not match:
        return None
    try:
        state = json.loads(json.loads(match.group(1)))
    except json.JSONDecodeError:
        return None
    for app in state.values():  # "app_cldp" aujourd'hui ; le nom de l'application peut changer
        classified = ((app or {}).get("data") or {}).get("classified")
        if classified:
            return classified
    return None


def _from_state(c: dict[str, Any]) -> ListingDetail:
    sections = c.get("sections") or {}
    hard_facts = sections.get("hardFacts") or {}
    price = hard_facts.get("price") or {}
    location = sections.get("location") or {}
    address = location.get("address") or {}
    coordinates = (location.get("geometry") or {}).get("coordinates") or []
    if len(coordinates) < 2:  # adresse non publiée : pas de point
        coordinates = [None, None]
    description = sections.get("description") or sections.get("mainDescription") or {}
    metadata = c.get("metadata") or {}
    tracking_items = (c.get("tracking") or {}).get("av_items") or [{}]
    provider = (c.get("contactSections") or {}).get("provider") or {}

    return ListingDetail(
        title=hard_facts.get("title"),
        headline=description.get("headline"),
        description=_clean_text(description.get("description")),
        price=_number(tracking_items[0].get("price")) or _number(price.get("value")),
        price_label=price.get("formatted") or price.get("value"),
        price_note=price.get("additionalInformation"),
        key_facts=hard_facts.get("keyfacts") or [f["value"] for f in hard_facts.get("facts", []) if f.get("value")],
        features=_features(sections.get("features") or {}),
        energy=_energy_scales(sections.get("energy") or {}),
        energy_features=_energy_features(sections.get("energy") or {}),
        costs=_costs(sections.get("price") or {}),
        price_comparison=_price_comparison(sections.get("priceComparison") or {}),
        city=address.get("city"),
        postal_code=address.get("zipCode"),
        district=address.get("district"),
        longitude=_number(coordinates[0]),
        latitude=_number(coordinates[1]),
        schools=_schools(location.get("schools") or {}),
        images=_images(c),
        virtual_tours=[t["url"] for t in ((c.get("domains") or {}).get("medias") or {}).get("virtualTours", []) if t.get("url")],
        tags=[label for key, label in TAGS.items() if (c.get("tags") or {}).get(key)],
        publisher_type=_publisher_type(provider),
        published_at=_date(metadata.get("creationDate")),
        updated_at=_date(metadata.get("updateDate")),
    )


def _features(features: dict[str, Any]) -> list[FeatureGroup]:
    categories = (features.get("details") or {}).get("categories") or []
    groups = [
        FeatureGroup(title=cat.get("title") or "", items=[e["value"] for e in cat.get("elements", []) if e.get("value")])
        for cat in categories
    ]
    if not groups and features.get("preview"):
        groups = [FeatureGroup(title="Caractéristiques", items=[e["value"] for e in features["preview"] if e.get("value")])]
    return [g for g in groups if g.items]


def _energy_scales(energy: dict[str, Any]) -> list[EnergyScale]:
    scales = []
    for certificate in energy.get("certificates") or []:
        for scale in certificate.get("scales") or []:
            scales.append(
                EnergyScale(
                    name=scale.get("name") or "",
                    rating=(scale.get("efficiencyClass") or {}).get("rating"),
                    values=[LabeledValue(label=v["label"], value=v["value"]) for v in scale.get("values", []) if v.get("value")],
                )
            )
    return scales


def _energy_features(energy: dict[str, Any]) -> list[LabeledValue]:
    items = [LabeledValue(label=f["label"], value=f["value"]) for f in energy.get("features") or [] if f.get("value")]
    for certificate in energy.get("certificates") or []:
        for f in certificate.get("features") or []:
            # « estimationDescription » est un texte technique mal formé (« [object Object] »).
            if f.get("value") and f.get("type") != "estimationDescription":
                items.append(LabeledValue(label=f["label"], value=f["value"]))
    return items


def _costs(price: dict[str, Any]) -> list[LabeledValue]:
    """Loyer ou prix, charges, honoraires, dépôt de garantie… (« dont » pour les montants inclus)."""
    costs: list[LabeledValue] = []
    for component in price.get("components") or []:
        for unit in component.get("units") or []:
            main = (unit.get("main") or {}).get("price")
            if main:
                costs.append(_cost(main))
            for detail in unit.get("details") or []:
                prefix = f"{detail['label']} " if detail.get("label") else ""
                costs.extend(_cost(p, prefix) for p in detail.get("prices") or [])
    return [c for c in costs if c.value]


def _cost(price: dict[str, Any], prefix: str = "") -> LabeledValue:
    value = (price.get("value") or {}).get("main") or {}
    return LabeledValue(label=f"{prefix}{(price.get('label') or {}).get('main', '')}".strip(), value=value.get("value") or "")


def _price_comparison(section: dict[str, Any]) -> PriceComparison | None:
    data = section.get("data") or {}
    if not data and not section.get("pricePerSqm"):
        return None
    return PriceComparison(
        price_per_m2=_number(section.get("pricePerSqm")),
        low=_number(data.get("low")),
        high=_number(data.get("high")),
        average=_number(data.get("value")),
    )


def _schools(schools: dict[str, Any]) -> list[School]:
    result = []
    for key, public in (("publicSchools", True), ("privateSchools", False)):
        for s in schools.get(key) or []:
            if s.get("name"):
                result.append(
                    School(
                        name=s["name"],
                        level=SCHOOL_LEVELS.get(s.get("type"), s.get("type")),
                        distance=s.get("distanceKm"),
                        public=public,
                    )
                )
    return result


def _images(c: dict[str, Any]) -> list[Image]:
    images = ((c.get("domains") or {}).get("medias") or {}).get("images") or []
    if not images:
        images = ((c.get("sections") or {}).get("gallery") or {}).get("images") or []
    seen, result = set(), []
    for img in images:
        url = img.get("url")
        if url and url not in seen:
            seen.add(url)
            result.append(Image(url=url, description=img.get("description")))
    return result


def _publisher_type(provider: dict[str, Any]) -> str | None:
    if provider.get("isPrivateOwner"):
        return "particulier"
    if provider.get("publisherType"):
        return "agence" if provider["publisherType"] == "AGENCY" else provider["publisherType"].lower()
    return None


# --------------------------------------------------------------------------- #
# HTML (secours)
# --------------------------------------------------------------------------- #


def _from_html(html: str) -> ListingDetail:
    soup = BeautifulSoup(html, "html.parser")
    listing = _json_ld_listing(soup)
    title = _testid(soup, "cdp-hardfacts-title")
    if not listing and not title:
        raise ParseError("Page d'annonce SeLoger illisible (annonce retirée, blocage ou format modifié)")

    offered = (listing or {}).get("itemOffered") or {}
    images = [m["content"] for m in soup.select('meta[property="og:image"]') if m.get("content")]
    keyfacts = _testid(soup, "cdp-hardfacts-keyfacts", sep="|") or ""
    return ListingDetail(
        title=title,
        headline=_testid(soup, "cdp-main-description-title") or offered.get("name"),
        description=_testid(soup, "cdp-main-description-expandable-text", sep="\n") or (listing or {}).get("description"),
        price=_number((((listing or {}).get("offers")) or {}).get("price")),
        key_facts=[f.strip() for f in re.split(r"[|•]", keyfacts) if f.strip()],
        city=_testid(soup, "cdp-location-address"),
        images=[Image(url=u) for u in dict.fromkeys(images)],
        published_at=_date((listing or {}).get("datePosted")),
    )


def _json_ld_listing(soup: BeautifulSoup) -> dict[str, Any] | None:
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("@type") == "RealEstateListing":
            return data
    return None


def _testid(soup: BeautifulSoup, testid: str, sep: str = " ") -> str | None:
    element = soup.select_one(f'[data-testid="{testid}"]')
    return " ".join(element.get_text(sep, strip=True).split(" ")) if element else None


# --------------------------------------------------------------------------- #


def _number(value: Any) -> float | None:
    """817 → 817.0 ; « 19,38 » → 19.38 ; « 1 940 € » → 1940.0."""
    if value is None or isinstance(value, bool) or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = _NUMBER_RE.search(re.sub(r"[\s  ]", "", str(value)))
    return float(match.group().replace(",", ".")) if match else None


def _date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _clean_text(text: str | None) -> str | None:
    if not text:
        return None
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\n{3,}", "\n\n", text).strip()
