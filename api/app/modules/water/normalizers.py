"""Transformation des réponses brutes Hub'Eau / VigiEau en lignes de la base (fonctions pures)."""

from ...geo_utils import point_wkt
from ...parse import int_, iso_date, num, parse_datetime, str_


def _first(*values):
    """Équivalent de `a ?? b ?? ...` : première valeur non None."""
    return next((v for v in values if v is not None), None)


def normalize_water(r: dict, stamp: dict) -> dict:
    networks = r.get("reseaux") or []
    network = (networks[0] or {}).get("nom") if networks else None
    return {
        "inseeCode": r.get("code_commune"),
        "sampleCode": r.get("code_prelevement"),
        "parameterCode": str(r.get("code_parametre")),
        "parameterLabel": _first(str_(r.get("libelle_parametre"), 255), str(r.get("code_parametre"))),
        "resultNumeric": num(r.get("resultat_numerique")),
        "resultText": str_(r.get("resultat_alphanumerique"), 32),
        "unit": str_(r.get("libelle_unite"), 24),
        "qualityLimit": str_(r.get("limite_qualite_parametre"), 64),
        "sampledAt": parse_datetime(r.get("date_prelevement")),
        "networkName": str_(_first(network, r.get("nom_uge")), 160),
        "distributor": str_(r.get("nom_distributeur"), 160),
        "physchemCompliance": str_(r.get("conformite_limites_pc_prelevement"), 1),
        "bacterioCompliance": str_(r.get("conformite_limites_bact_prelevement"), 1),
        "conclusion": str_(r.get("conclusion_conformite_prelevement"), 1000),
        **stamp,
    }


def normalize_groundwater_station(s: dict, m: dict | None, stamp: dict) -> dict:
    """`m` : dernière mesure de la chronique de la station (None si non interrogée)."""
    m = m or {}
    return {
        "codeBss": s["code_bss"],
        "bssId": str_(s.get("bss_id"), 16),
        "inseeCode": str_(s.get("code_commune_insee"), 5),
        "communeName": str_(s.get("nom_commune"), 120),
        "altitudeM": num(s.get("altitude_station")),
        "depthM": num(s.get("profondeur_investigation")),
        "measuresCount": int_(s.get("nb_mesures_piezo")),
        "firstMeasureDate": iso_date(s.get("date_debut_mesure")),
        "lastMeasureDate": iso_date(_first(m.get("date_mesure"), s.get("date_fin_mesure"))),
        "lastWaterDepthM": num(m.get("profondeur_nappe")),
        "lastLevelNgfM": num(m.get("niveau_nappe_eau")),
        "latitude": s["y"],
        "longitude": s["x"],
        "location": point_wkt(s["x"], s["y"]),
        **stamp,
    }


def normalize_drought_zone(z: dict, insee: str, zone_type: str, stamp: dict) -> dict:
    decree = z.get("arrete") or {}
    return {
        "inseeCode": insee,
        "zoneId": z.get("id"),
        "zoneCode": str_(z.get("code"), 32),
        "zoneName": str_(z.get("nom"), 160),
        "zoneType": _first(z.get("type"), zone_type),
        "severity": _first(z.get("niveauGravite"), "inconnu"),
        "decreeStart": iso_date(decree.get("dateDebutValidite")),
        "decreeEnd": iso_date(decree.get("dateFinValidite")),
        "decreeUrl": str_(decree.get("cheminFichier"), 500),
        "usages": [
            {"name": u.get("nom"), "theme": u.get("thematique"), "description": u.get("description")}
            for u in z.get("usages") or []
        ],
        **stamp,
    }
