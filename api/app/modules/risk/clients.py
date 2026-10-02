"""
Géorisques API v1. Endpoints vérifiés le 2026-10-02.
Obsolètes / défaillants : /rga (corps vide), /tri, /canalisations, /remontees_nappes (404),
/gaspar/pprn (ignore le filtre code_insee). Le « rapport de risque » couvre ces aléas à l'adresse.
"""

from ...http_client import http

BASE = "https://georisques.gouv.fr/api/v1"


async def _get(path: str, params: dict):
    return await http.get(f"{BASE}/{path}", source="georisques", params=params, timeout_ms=45000)


def _data(res) -> list:
    return (res.get("data") if isinstance(res, dict) else None) or []


async def _first(path: str, params: dict) -> dict | None:
    data = _data(await _get(path, params))
    return data[0] if data else None


async def _paged(path: str, params: dict, max_pages: int = 10) -> list[dict]:
    """Toutes les pages d'un endpoint paginé (`data`, `total_pages`)."""
    out: list[dict] = []
    for page in range(1, max_pages + 1):
        res = await _get(path, {**params, "page": page, "page_size": 50})
        out.extend(_data(res))
        total_pages = res.get("total_pages") if isinstance(res, dict) else None
        if not total_pages or page >= total_pages:
            break
    return out


def _latlon(p: dict) -> str:
    return f"{p['lon']},{p['lat']}"


async def report(p: dict):
    return await _get("resultats_rapport_risque", {"latlon": _latlon(p)})


async def radon(insee: str) -> dict | None:
    return await _first("radon", {"code_insee": insee})


async def seismic_zone(insee: str) -> dict | None:
    return await _first("zonage_sismique", {"code_insee": insee})


async def commune_risks(insee: str) -> dict | None:
    return await _first("gaspar/risques", {"code_insee": insee})


async def flood_atlases(insee: str) -> list[dict]:
    return await _paged("gaspar/azi", {"code_insee": insee}, 2)


async def catnat(insee: str) -> list[dict]:
    return await _paged("gaspar/catnat", {"code_insee": insee}, 20)


async def cavities(p: dict, radius_m: int) -> list[dict]:
    return await _paged("cavites", {"latlon": _latlon(p), "rayon": radius_m}, 5)


async def ground_movements(p: dict, radius_m: int) -> list[dict]:
    return await _paged("mvt", {"latlon": _latlon(p), "rayon": radius_m}, 5)


async def polluted_soils(p: dict, radius_m: int):
    """Sols pollués : réponse groupée par base ({ casias: {data}, ... })."""
    return await _get("ssp", {"latlon": _latlon(p), "rayon": radius_m, "page_size": 50})


async def installations(p: dict, radius_m: int) -> list[dict]:
    return await _paged("installations_classees", {"latlon": _latlon(p), "rayon": radius_m}, 6)
