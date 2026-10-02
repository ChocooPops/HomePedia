"""Récupération brute (aucune transformation) des sources du module bâtiment."""

import csv
import io
import re

from ...config import settings
from ...http_client import http
from ...open_data import datafair_lines, tabular_query

RNB_BASE = "https://rnb-api.beta.gouv.fr/api/alpha"

# BDNB (API PostgREST). Lien RNB -> BDNB via la table batiment_construction.
BDNB_BASE = "https://api.bdnb.io/v1/bdnb/donnees"
BDNB_FIELDS = ",".join([
    "batiment_groupe_id", "code_commune_insee", "annee_construction", "hauteur_mean", "nb_niveau", "nb_log",
    "mat_mur_txt", "mat_toit_txt", "usage_niveau_1_txt", "classe_bilan_dpe", "numero_immat_principal",
    "code_iris", "surface_emprise_sol", "altitude_sol_mean", "l_parcelle_id",
])

DPE_DATASET = "https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant"
DPE_FIELDS = ",".join([
    "numero_dpe", "date_etablissement_dpe", "etiquette_dpe", "etiquette_ges", "conso_5_usages_par_m2_ep",
    "emission_ges_5_usages_par_m2", "annee_construction", "periode_construction", "type_batiment",
    "surface_habitable_logement", "hauteur_sous_plafond", "type_energie_principale_chauffage", "cout_total_5_usages",
    "id_rnb", "identifiant_ban", "adresse_ban", "code_insee_ban", "_geopoint",
])

# DVF géolocalisé : un CSV par commune et par année (2021 -> dernière année publiée).
DVF_BASE = "https://files.data.gouv.fr/geo-dvf/latest/csv"

# Registre national des copropriétés (RNIC) via l'API tabulaire data.gouv.
# « Registre d'Immatriculation des Copropriétés T3 2025 - nouveau format de colonnes ».
RNIC_RESOURCE_ID = "cc062fa7-4a80-449c-ab73-d2856b455ec9"


# ------------------------------------------------------------------ RNB


async def rnb_closest(p: dict, radius_m: int = 30) -> list[dict]:
    """Bâtiments les plus proches d'un point (triés par distance)."""
    res = await http.get(
        f"{RNB_BASE}/buildings/closest/", source="rnb", params={"point": f"{p['lat']},{p['lon']}", "radius": radius_m}
    )
    results = res.get("results")
    return results if results is not None else []


# ----------------------------------------------------------------- BDNB


def _bdnb_headers() -> dict:
    key = settings.bdnb_api_key
    return {"X-Gravitee-Api-Key": key} if key else {}


async def bdnb_group_id_for_rnb(rnb_id: str) -> str | None:
    rows = await http.get(
        f"{BDNB_BASE}/batiment_construction",
        source="bdnb",
        headers=_bdnb_headers(),
        params={"rnb_id": f"eq.{rnb_id}", "select": "batiment_groupe_id", "limit": 1},
    )
    return rows[0].get("batiment_groupe_id") if rows else None


async def bdnb_group(group_id: str) -> dict | None:
    rows = await http.get(
        f"{BDNB_BASE}/batiment_groupe_complet",
        source="bdnb",
        headers=_bdnb_headers(),
        params={"batiment_groupe_id": f"eq.{group_id}", "select": BDNB_FIELDS, "limit": 1},
    )
    return rows[0] if rows else None


# ------------------------------------------------------------------ DPE


async def dpe_near(p: dict, radius_m: int = 30, max_rows: int = 200) -> list[dict]:
    """DPE géolocalisés dans un rayon (m) autour du point."""
    return await datafair_lines(
        "ademe_dpe", DPE_DATASET, {"geo_distance": f"{p['lon']},{p['lat']},{radius_m}", "select": DPE_FIELDS}, max_rows
    )


async def dpe_by_rnb(rnb_id: str, max_rows: int = 200) -> list[dict]:
    return await datafair_lines("ademe_dpe", DPE_DATASET, {"id_rnb_eq": rnb_id, "select": DPE_FIELDS}, max_rows)


# ------------------------------------------------------------------ DVF


async def dvf_available_years() -> list[int]:
    html = await http.get(f"{DVF_BASE}/", source="dvf", text=True)
    return sorted({int(y) for y in re.findall(r'href="[^"]*?(\d{4})/"', html)})


async def dvf_commune_year(insee: str, year: int) -> list[dict[str, str]]:
    dep = insee[:3] if insee.startswith("97") else insee[:2]
    text = await http.get(
        f"{DVF_BASE}/{year}/communes/{dep}/{insee}.csv", source="dvf", text=True, allow_statuses=(404,), timeout_ms=120000
    )
    if not text or text.startswith("<"):
        return []
    rows = []
    for row in csv.DictReader(io.StringIO(text, newline="")):
        # Un fichier dont une ligne n'a pas le même nombre de colonnes que l'en-tête est refusé en bloc.
        if None in row or any(v is None for v in row.values()):
            raise ValueError(f"CSV DVF invalide ({insee}, {year}) : nombre de colonnes incohérent")
        rows.append(row)
    return rows


# ----------------------------------------------------------------- RNIC


async def rnic_by_registration(numero: str) -> list[dict]:
    return await tabular_query("rnic", RNIC_RESOURCE_ID, {"numero_d_immatriculation": numero}, max_rows=5)


async def rnic_by_parcel(idu: str) -> list[dict]:
    return await tabular_query("rnic", RNIC_RESOURCE_ID, {"reference_cadastrale_1": idu}, max_rows=20)
