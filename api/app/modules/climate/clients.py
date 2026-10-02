"""Récupération brute (aucune transformation) : Open-Meteo (réanalyse, projections), PVGIS, Atmo France."""

import time

from ...config import settings
from ...errors import MissingApiKeyError
from ...http_client import http

ARCHIVE_DAILY_VARS = [
    "temperature_2m_min", "temperature_2m_max", "snowfall_sum", "wind_gusts_10m_max", "sunshine_duration", "precipitation_sum",
]

# Modèles CMIP6 HighResMIP d'Open-Meteo retenus (EC_Earth3P_HR renvoie des valeurs nulles après 2049).
# Open-Meteo facture les requêtes au volume (variables × durée) : 3 modèles × 2 périodes de 10 ans
# restent sous le quota gratuit de 600 « appels » par minute.
CLIMATE_MODELS = ["MRI_AGCM3_2_S", "CMCC_CM2_VHR4", "MPI_ESM1_2_XR"]

ATMO_BASE = "https://admindata.atmo-france.org/api"
_atmo_token: dict | None = None  # { "value": jeton, "expires": instant (s) }


async def open_meteo_archive(p: dict, start: str, end: str) -> dict:
    return await http.get(
        "https://archive-api.open-meteo.com/v1/archive",
        source="open_meteo_archive",
        params={
            "latitude": p["lat"],
            "longitude": p["lon"],
            "start_date": start,
            "end_date": end,
            "daily": ",".join(ARCHIVE_DAILY_VARS),
            "timezone": "Europe/Paris",
        },
        timeout_ms=60000,
    )


async def open_meteo_climate(p: dict, start: str, end: str) -> dict:
    return await http.get(
        "https://climate-api.open-meteo.com/v1/climate",
        source="open_meteo_climate",
        params={
            "latitude": p["lat"],
            "longitude": p["lon"],
            "start_date": start,
            "end_date": end,
            "models": ",".join(CLIMATE_MODELS),
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        },
        timeout_ms=90000,
    )


async def pvgis_pvcalc(p: dict) -> dict:
    """Production d'un système de 1 kWc, inclinaison/orientation optimales, masque d'horizon topographique inclus."""
    return await http.get(
        "https://re.jrc.ec.europa.eu/api/v5_3/PVcalc",
        source="pvgis",
        params={
            "lat": p["lat"], "lon": p["lon"], "peakpower": 1, "loss": 14, "optimalangles": 1, "usehorizon": 1,
            "outputformat": "json",
        },
    )


# Atmo France (indice ATMO et pollens). Authentification par compte : POST /login -> jeton.
# Non testé faute de compte : implémenté d'après la documentation publique de l'API.


async def _atmo_auth() -> str:
    global _atmo_token
    username, password = settings.atmo_username, settings.atmo_password
    if not username or not password:
        raise MissingApiKeyError("atmo", "ATMO_USERNAME / ATMO_PASSWORD")
    if _atmo_token and _atmo_token["expires"] > time.time():
        return _atmo_token["value"]
    res = await http.post(f"{ATMO_BASE}/login", {"username": username, "password": password}, source="atmo")
    _atmo_token = {"value": res["token"], "expires": time.time() + 20 * 3600}
    return res["token"]


async def atmo_indices(kind: str, insee: str, date: str) -> list[dict]:
    """`kind` : « atmo » ou « pollens »."""
    token = await _atmo_auth()
    res = await http.get(
        f"{ATMO_BASE}/v2/data/indices/{kind}",
        source="atmo",
        headers={"Authorization": f"Bearer {token}"},
        params={"format": "geojson", "code_zone": insee, "date": date, "date_historique": date},
    )
    return res.get("features") or []
