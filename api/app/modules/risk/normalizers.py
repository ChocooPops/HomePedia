"""Transformation des réponses Géorisques en lignes de la base (fonctions pures, testables)."""

import json
import re

from ...geo_utils import point_wkt
from ...parse import int_, iso_date, num, str_

REPORT_GROUPS = (("risquesNaturels", "natural"), ("risquesTechnologiques", "technological"))
# Colonnes facultatives d'un site : toutes présentes (None par défaut) pour que les lignes d'un même upsert soient homogènes.
SITE_FIELDS = ("name", "inseeCode", "status", "sevesoStatus", "subtype", "details")
ICPE_ACTIVITIES = ("bovins", "porcs", "volailles", "carriere", "eolienne", "industrie")


def _coalesce(*values):
    """Équivalent de `a ?? b` : première valeur non nulle (0 et '' sont conservés)."""
    return next((v for v in values if v is not None), None)


def _pick(src: dict, keys: dict[str, str]) -> dict:
    """{ clé de sortie: src[clé source] } ; une clé absente de la source est omise."""
    return {out: src[key] for out, key in keys.items() if key in src}


def normalize_report(report: dict | None, address_id: int, stamp: dict) -> list[dict]:
    out = []
    for key, category in REPORT_GROUPS:
        for hazard_code, r in ((report or {}).get(key) or {}).items():
            out.append({
                "addressId": address_id,
                "hazardCode": hazard_code,
                "category": category,
                "label": _coalesce(r.get("libelle"), hazard_code),
                "present": bool(r.get("present")),
                "communeStatus": str_(r.get("libelleStatutCommune"), 80),
                "addressStatus": str_(r.get("libelleStatutAdresse"), 80),
                "details": r.get("specifique"),
                **stamp,
            })
    return out


def normalize_commune_profile(
    insee: str, radon: dict | None, seismic: dict | None, risks: dict | None, azi: list[dict], stamp: dict
) -> dict:
    return {
        "inseeCode": insee,
        "radonClass": int_((radon or {}).get("classe_potentiel")),
        "seismicZone": str_((seismic or {}).get("zone_sismicite"), 32),
        "knownRisks": [r.get("libelle_risque_long") for r in (risks or {}).get("risques_detail") or []],
        "floodAtlases": [
            {**_pick(a, {"code": "code_national_azi", "label": "libelle_azi"}), "published": iso_date(a.get("date_diffusion"))}
            for a in azi
        ],
        **stamp,
    }


def normalize_catnat(r: dict, stamp: dict) -> dict:
    return {
        "codeNational": r.get("code_national_catnat"),
        "inseeCode": r.get("code_insee"),
        "hazardLabel": _coalesce(str_(r.get("libelle_risque_jo"), 160), "Inconnu"),
        "eventStart": iso_date(r.get("date_debut_evt")),
        "eventEnd": iso_date(r.get("date_fin_evt")),
        "decreeDate": iso_date(r.get("date_publication_arrete")),
        "journalDate": iso_date(r.get("date_publication_jo")),
        **stamp,
    }


def _site(site_type: str, external_id, lat: float | None, lon: float | None, fields: dict, stamp: dict) -> dict | None:
    if not external_id or lat is None or lon is None:
        return None
    return {
        "siteType": site_type,
        "externalId": str(external_id)[:64],
        "latitude": lat,
        "longitude": lon,
        "location": point_wkt(lon, lat),
        **{k: fields.get(k) for k in SITE_FIELDS},
        **stamp,
    }


def _representative_point(geom: dict | None) -> dict | None:
    """Point représentatif d'une géométrie GeoJSON (centre de l'emprise)."""
    if not geom:
        return None
    if geom.get("type") == "Point":
        return {"lon": geom["coordinates"][0], "lat": geom["coordinates"][1]}
    flat = json.dumps(geom.get("coordinates"), separators=(",", ":"))
    coords = [[float(x) for x in m.group(0).split(",")] for m in re.finditer(r"-?\d+(\.\d+)?,-?\d+(\.\d+)?", flat)]
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return {"lon": (min(lons) + max(lons)) / 2, "lat": (min(lats) + max(lats)) / 2}


def normalize_cavity(r: dict, stamp: dict) -> dict | None:
    return _site("cavity", r.get("identifiant"), num(r.get("latitude")), num(r.get("longitude")), {
        "name": str_(r.get("nom"), 255), "subtype": str_(r.get("type"), 120), "inseeCode": str_(r.get("code_insee"), 5),
    }, stamp)


def normalize_ground_movement(r: dict, stamp: dict) -> dict | None:
    return _site("ground_movement", r.get("identifiant"), num(r.get("latitude")), num(r.get("longitude")), {
        "name": str_(r.get("lieu"), 255), "subtype": str_(r.get("type"), 120), "inseeCode": str_(r.get("code_insee"), 5),
        "details": _pick(r, {"date": "date_debut", "reliability": "fiabilite", "comment": "commentaire_mvt"}),
    }, stamp)


def normalize_polluted_soils(res: dict | None, stamp: dict) -> list[dict | None]:
    out: list[dict | None] = []
    for base, block in (res if isinstance(res, dict) else {}).items():
        for r in (block.get("data") if isinstance(block, dict) else None) or []:
            p = _representative_point(r.get("geom"))
            out.append(_site(
                "casias" if base == "casias" else "ssp",
                _coalesce(r.get("identifiant_ssp"), r.get("identifiant_casias")),
                p["lat"] if p else None,
                p["lon"] if p else None,
                {
                    "name": str_(_coalesce(r.get("nom_etablissement"), r.get("adresse")), 255),
                    "subtype": str_(_coalesce(r.get("activite_principale"), base), 120),
                    "status": str_(r.get("statut"), 80),
                    "inseeCode": str_(r.get("code_insee"), 5),
                    "details": _pick(r, {"address": "adresse", "sheet": "fiche_risque"}),
                },
                stamp,
            ))
    return out


def normalize_installation(r: dict, stamp: dict) -> dict | None:
    activities = [k for k in ICPE_ACTIVITIES if r.get(k)]
    return _site("icpe", r.get("codeAIOT"), num(r.get("latitude")), num(r.get("longitude")), {
        "name": str_(r.get("raisonSociale"), 255),
        "inseeCode": str_(r.get("codeInsee"), 5),
        "status": str_(_coalesce(r.get("etatActivite"), r.get("regime")), 80),
        "sevesoStatus": str_(r.get("statutSeveso"), 48),
        "subtype": ",".join(activities) or str_(r.get("codeNaf"), 120),
        "details": _pick(r, {"regime": "regime", "naf": "codeNaf", "siret": "siret", "ied": "ied", "priority": "prioriteNationale"}),
    }, stamp)
