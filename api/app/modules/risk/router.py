import ipaddress
import re
from typing import Annotated, Literal, get_args

from fastapi import APIRouter, Query
from pydantic import Field, field_validator

from ...schemas import AddressId, CollectQuery, InseeCode, RadiusQuery, StrictModel
from ..geo import service as geo
from . import service

router = APIRouter(tags=["risk"])

BioSpecies = Literal["tiger_mosquito", "asian_hornet", "termite", "dry_rot", "wolf", "wild_boar", "tick_lyme", "bed_bug", "rat"]
BIO_SPECIES = get_args(BioSpecies)

_FQDN_LABEL = re.compile(r"^[a-z¡-￿0-9-]+$", re.IGNORECASE)
_FQDN_TLD = re.compile(r"^([a-z¡-￿]{2,}|xn[a-z0-9-]{2,})$", re.IGNORECASE)


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _is_fqdn(host: str) -> bool:
    parts = host.split(".")
    if len(parts) < 2 or not _FQDN_TLD.match(parts[-1]):
        return False
    return all(_FQDN_LABEL.match(p) and len(p) <= 63 and not p.startswith("-") and not p.endswith("-") for p in parts)


def is_url(url: str) -> bool:
    """
    Mêmes règles que `@IsUrl()` de class-validator (validator.js, options par défaut) : protocole facultatif
    mais limité à http, https ou ftp, hôte = nom de domaine avec TLD ou adresse IP, port facultatif.
    """
    if not url or len(url) >= 2083 or re.search(r"[\s<>]", url) or url.startswith("mailto:"):
        return False
    rest = url.split("#")[0].split("?")[0]
    if "://" in rest:
        protocol, rest = rest.split("://", 1)
        if protocol.lower() not in ("http", "https", "ftp"):
            return False
    elif rest.startswith("//"):
        return False
    authority = rest.split("/")[0]
    if not authority:
        return False
    if "@" in authority:
        auth, authority = authority.split("@", 1)
        if not auth or (":" in auth and len(auth.split(":")) > 2):
            return False
    ipv6 = re.match(r"^\[([^\]]+)\](?::([0-9]+))?$", authority)
    if ipv6:
        host, port = ipv6[1], ipv6[2]
    else:
        host, _, port = authority.partition(":")
        port = port or None
        if authority.endswith(":") or authority.count(":") > 1:
            return False
    if port is not None and (not port.isdigit() or not 0 < int(port) <= 65535):
        return False
    if not host:
        return False
    return _is_ip(host) or (not ipv6 and _is_fqdn(host))


class BioRisk(StrictModel):
    scope: Literal["commune", "department"]
    areaCode: str = Field(
        pattern=r"^(\d{2,3}|2[AB]|\d{5}|2[AB]\d{3})$", description="Code INSEE commune ou code département", examples=["80"]
    )
    species: BioSpecies
    status: str = Field(max_length=80, examples=["colonisé"])
    year: int = Field(ge=1990, le=2100, examples=[2026])
    referenceUrl: str | None = None
    notes: str | None = Field(None, max_length=500)

    @field_validator("referenceUrl")
    @classmethod
    def _url(cls, v: str | None) -> str | None:
        if v is not None and not is_url(v):
            raise ValueError("referenceUrl must be a URL address")
        return v


class BioRiskBatch(StrictModel):
    items: list[BioRisk] = Field(min_length=1)


class BioRiskQuery(StrictModel):
    areaCode: str | None = Field(None, examples=["80"])
    species: str | None = Field(None, examples=["tiger_mosquito,termite"])


@router.post(
    "/addresses/{id}/risks/collect",
    status_code=201,
    summary="Collecte Géorisques (rapport, radon, sismicité, CatNat, sites ICPE/SSP/cavités) + OLD",
)
async def collect(id: AddressId, q: Annotated[CollectQuery, Query()]):
    return await service.collect(await geo.get_address(id), q.force)


@router.get("/addresses/{id}/risks", summary="Synthèse des risques à l’adresse")
async def read(id: AddressId, q: Annotated[RadiusQuery, Query()]):
    return await service.read(await geo.get_address(id), q.radius if q.radius is not None else 1000)


@router.get("/communes/{insee}/catnat", summary="Historique des arrêtés de catastrophe naturelle de la commune")
async def catnat(insee: InseeCode):
    return await service.catnat_of(insee)


@router.post(
    "/bio-risks",
    status_code=201,
    summary="Saisie / import de risques biologiques (aucune API nationale : moustique tigre, termites...)",
)
async def upsert_bio(dto: BioRiskBatch):
    # exclude_unset : une propriété facultative non transmise reste absente (elle n'écrase pas la valeur en base).
    await service.upsert_bio_risks([i.model_dump(exclude_unset=True) for i in dto.items])
    return {"upserted": len(dto.items)}


@router.get("/bio-risks", summary="Liste des risques biologiques saisis")
async def list_bio(q: Annotated[BioRiskQuery, Query()]):
    return await service.list_bio_risks(q.areaCode, q.species)
