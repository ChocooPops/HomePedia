"""Récupération brute (aucune transformation) des sources socio-démographiques."""

from ...config import settings
from ...http_client import http
from ...open_data import ods_records, tabular_query

MELODI_BASE = "https://api.insee.fr/melodi"
# SSMSI : base communale de la délinquance enregistrée (fichier publié sur data.gouv.fr).
SSMSI_RESOURCE_ID = "44ef4323-1097-48d5-8719-3c544b55d294"


async def melodi_observations(dataset: str, filters: dict) -> list[dict]:
    """INSEE Melodi (recensement). Accès anonyme possible, quota relevé avec une clé."""
    key = settings.insee_api_key
    res = await http.get(
        f"{MELODI_BASE}/data/{dataset}",
        source="insee_melodi",
        headers={"X-INSEE-Api-Key-Integration": key} if key else {},
        params={**filters, "maxResult": 1000},
        timeout_ms=60000,
    )
    return res.get("observations") or []


async def fiscalite_by_commune(insee: str) -> list[dict]:
    return await ods_records(
        "fiscalite_locale",
        "https://data.economie.gouv.fr/api/explore/v2.1",
        "fiscalite-locale-des-particuliers",
        {"where": f'insee_com="{insee}"', "order_by": "exercice DESC"},
        20,
    )


async def ssmsi_by_commune(insee: str) -> list[dict]:
    return await tabular_query("ssmsi", SSMSI_RESOURCE_ID, {"CODGEO_2026": insee}, max_rows=600)
