"""Normalisation des réponses FCU, GRDF et Enedis en lignes de base."""

import re

from ...parse import int_, normalize_label, num, str_

COMMUNE_KEY = "__COMMUNE__"

# Clé de `details` -> champ de la réponse FCU.
_HEAT_DETAILS = {
    "networkId": "id", "renewableRate": "rateENRR", "co2Rate": "rateCO2", "futureNetwork": "futurNetwork", "priorityZone": "inPDP",
}


def enedis_address_key(housenumber: str | None, street: str | None) -> str | None:
    """Abréviations de type de voie utilisées par Enedis (« 2 RUE DE LA REPUBLIQUE »)."""
    if not housenumber or not street:
        return None
    return normalize_label(f"{housenumber} {street}")


def normalize_heat_network(res: dict, address_id: int, stamp: dict) -> dict:
    return {
        "addressId": address_id,
        "networkType": "heat",
        "available": bool(res.get("isEligible")),
        "distanceM": int_(res.get("distance")),
        "operatorName": str_(res.get("gestionnaire"), 160),
        "networkName": str_(res.get("name"), 160),
        # Un champ absent de la réponse n'est pas écrit.
        "details": {key: res[field] for key, field in _HEAT_DETAILS.items() if field in res},
        **stamp,
    }


def normalize_gas_network(rows: list[dict], address_id: int, stamp: dict) -> dict:
    served = any(re.search("service", "" if r.get("etat_serv") is None else str(r["etat_serv"]), re.IGNORECASE) for r in rows)
    return {
        "addressId": address_id,
        "networkType": "gas",
        "available": served,
        "distanceM": None,
        "operatorName": "GRDF" if served else None,
        "networkName": None,
        "details": {
            "scope": "commune",
            "propane": rows[0].get("propane") if rows else None,
            "note": "Commune desservie par GRDF ; le raccordement du logement n’est pas publié",
        },
        **stamp,
    }


def normalize_consumption(r: dict, insee: str, address_key: str, stamp: dict) -> dict:
    commune = address_key == COMMUNE_KEY
    return {
        "inseeCode": insee,
        "addressKey": address_key,
        "year": int_(r.get("annee")),
        "irisCode": None if commune else str_(r.get("code_iris"), 9),
        "dwellings": None if commune else int_(r.get("nombre_de_logements")),
        "totalMwh": None if commune else num(r.get("consommation_annuelle_totale_de_ladresse_mwh")),
        "avgPerSiteMwh": None if commune else num(r.get("consommation_annuelle_moyenne_par_site_de_ladresse_mwh")),
        "communeAvgMwh": num(r.get("consommation_annuelle_moyenne_de_la_commune_mwh")),
        **stamp,
    }
