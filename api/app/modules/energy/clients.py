"""Récupération brute des sources du module énergie : France Chaleur Urbaine, GRDF, Enedis."""

from ...http_client import http
from ...open_data import datafair_lines, ods_records

FCU_ELIGIBILITY_URL = "https://france-chaleur-urbaine.beta.gouv.fr/api/v1/eligibility"
ENEDIS_RESIDENTIAL_BY_ADDRESS = "https://opendata.enedis.fr/data-fair/api/v1/datasets/msevy38s3ddly25n79bh8v-r"
GRDF_BASE = "https://opendata.grdf.fr/api/explore/v2.1"


async def fcu_eligibility(p: dict) -> dict:
    return await http.get(FCU_ELIGIBILITY_URL, source="fcu", params={"lat": p["lat"], "lon": p["lon"]})


async def grdf_network(insee: str) -> list[dict]:
    return await ods_records(
        "grdf",
        GRDF_BASE,
        "cartographie-du-reseau-grdf-en-service",
        {"where": f'code_insee_administratif="{insee}"', "select": "etat_serv,propane,code_insee_administratif"},
        5,
    )


async def enedis_by_address(insee: str, address_key: str) -> list[dict]:
    return await datafair_lines("enedis", ENEDIS_RESIDENTIAL_BY_ADDRESS, {"code_commune_eq": insee, "adresse_eq": address_key}, 50)


async def enedis_latest_of_commune(insee: str) -> list[dict]:
    return await datafair_lines("enedis", ENEDIS_RESIDENTIAL_BY_ADDRESS, {"code_commune_eq": insee, "sort": "-annee"}, 1)
