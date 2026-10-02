"""Lecture des CSV ARCEP et transformation en lignes de la base (fonctions pures, testables)."""

import csv
import io

from ...geo_utils import point_wkt
from ...parse import int_, js_round, num, str_


def parse_csv(text: str, *, relax_column_count: bool = False) -> list[dict]:
    """
    CSV à en-têtes, séparateur « ; », lignes vides ignorées.
    Sans `relax_column_count`, une ligne dont le nombre de colonnes diffère de l'en-tête est une erreur ;
    avec, les colonnes manquantes sont absentes (None) et les colonnes en trop ignorées.
    """
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    rows = []
    for row in reader:
        extra = row.pop(None, None)
        if not relax_column_count:
            got = len(row) + len(extra or []) - sum(1 for v in row.values() if v is None)
            if got != len(reader.fieldnames):
                raise ValueError(
                    f"Invalid Record Length: columns length is {len(reader.fieldnames)}, got {got} on line {reader.line_num}"
                )
        rows.append(row)
    return rows


def _int_or_zero(v) -> int:
    n = int_(v)
    return n if n is not None else 0


def normalize_fixed(r: dict, stamp: dict) -> dict | None:
    """Une ligne par commune : nombre de locaux et locaux éligibles par technologie."""
    if r.get("type") != "all" or not r.get("code_insee"):
        return None
    premises = _int_or_zero(r.get("nbr"))
    ftth = _int_or_zero(r.get("elig_ftth"))
    return {
        "inseeCode": r["code_insee"].rjust(5, "0"),
        "periodDate": r.get("date"),
        "premises": premises,
        "ftthEligible": ftth,
        "cableEligible": _int_or_zero(r.get("elig_coax")),
        "copperEligible": _int_or_zero(r.get("elig_cu")),
        "thdRadioEligible": _int_or_zero(r.get("elig_thdr")),
        "fixed4gEligible": _int_or_zero(r.get("elig_4gf")),
        "satelliteEligible": _int_or_zero(r.get("elig_sat")),
        "ftthRate": js_round(ftth / premises * 10000) / 100 if premises else None,
        **stamp,
    }


def normalize_site(r: dict, stamp: dict) -> dict | None:
    lat = num(r.get("latitude"))
    lon = num(r.get("longitude"))
    if not r.get("code_op") or not r.get("num_site") or lat is None or lon is None:
        return None

    def flag(k: str) -> bool:
        return r.get(k) == "1"

    return {
        "operatorCode": r["code_op"],
        "siteNumber": r["num_site"],
        "operatorName": r.get("nom_op"),
        "anfrStationId": str_(r.get("id_station_anfr"), 24),
        "inseeCode": r["insee_com"].rjust(5, "0") if r.get("insee_com") else None,
        "has2g": flag("site_2g"),
        "has3g": flag("site_3g"),
        "has4g": flag("site_4g"),
        "has5g": flag("site_5g"),
        "has5g3500": flag("site_5g_3500_m_hz"),
        "latitude": lat,
        "longitude": lon,
        "location": point_wkt(lon, lat),
        **stamp,
    }
