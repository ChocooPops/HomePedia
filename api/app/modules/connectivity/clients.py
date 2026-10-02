"""Récupération brute (aucune transformation) des fichiers nationaux ARCEP."""

from urllib.parse import urljoin

from ...http_client import http

FIXED_URL = "https://data.arcep.fr/fixe/maconnexioninternet/statistiques/last/commune/commune_techno.csv"
MOBILE_DIR = "https://data.arcep.fr/mobile/sites/last/"


def _without_bom(text: str) -> str:
    # Sans ce retrait, la marque d'ordre d'octets resterait collée au premier en-tête CSV.
    return text.removeprefix("﻿")


async def fixed_csv() -> str:
    return _without_bom(await http.get(FIXED_URL, source="arcep_fixe", text=True, timeout_ms=120000))


async def mobile_listing() -> str:
    return await http.get(MOBILE_DIR, source="arcep_mobile", text=True)


async def mobile_sites_csv(file: str) -> str:
    return _without_bom(await http.get(urljoin(MOBILE_DIR, file), source="arcep_mobile", text=True, timeout_ms=300000))
