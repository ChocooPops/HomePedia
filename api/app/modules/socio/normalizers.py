"""Transformation des réponses brutes en lignes de la base (fonctions pures, testables)."""

from ...parse import bool_from_flag, int_, js_round, num, str_

# Tranches d'âge disjointes du recensement et leur âge médian, pour estimer l'âge moyen.
AGE_BRACKETS = {"Y_LT15": 7.5, "Y15T24": 19.5, "Y25T39": 32, "Y40T54": 47, "Y55T64": 59.5, "Y65T79": 72, "Y_GE80": 86}


def _round(v: float, d: int = 2) -> float:
    return js_round(v * 10**d) / 10**d


def _value(o: dict | None):
    return num((((o or {}).get("measures") or {}).get("OBS_VALUE_NIVEAU") or {}).get("value"))


def _year(y) -> int | float | None:
    """La période arrive en chaîne (« 2023 »)."""
    return num(y)


def _periods(obs: list[dict]) -> list:
    return list(dict.fromkeys(o["dimensions"].get("TIME_PERIOD") for o in obs))


def population_indicators(obs: list[dict], insee: str, stamp: dict) -> list[dict]:
    out: list[dict] = []
    for y in _periods(obs):
        rows = [o for o in obs if o["dimensions"].get("TIME_PERIOD") == y and o["dimensions"].get("SEX") == "_T"]

        def get(age: str, rows=rows):
            return _value(next((o for o in rows if o["dimensions"].get("AGE") == age), None))

        total = get("_T")
        if not total:
            continue
        year = _year(y)
        out.append({"inseeCode": insee, "indicator": "population", "year": year, "value": js_round(total), "unit": "habitants", **stamp})
        brackets = [(n if (n := get(k)) is not None else 0, mid) for k, mid in AGE_BRACKETS.items()]
        covered = sum(n for n, _ in brackets)
        if covered > 0:
            out.append({
                "inseeCode": insee, "indicator": "mean_age_estimated", "year": year,
                "value": _round(sum(n * m for n, m in brackets) / covered, 1), "unit": "ans", **stamp,
            })
        over65 = get("Y_GE65")
        if over65 is not None:
            out.append({"inseeCode": insee, "indicator": "share_65_plus", "year": year, "value": _round(over65 / total * 100), "unit": "%", **stamp})
        under20 = get("Y_LT20")
        if under20 is not None:
            out.append({"inseeCode": insee, "indicator": "share_under_20", "year": year, "value": _round(under20 / total * 100), "unit": "%", **stamp})
    return out


def housing_indicators(occupancy: list[dict], stay: list[dict], insee: str, stamp: dict) -> list[dict]:
    out: list[dict] = []
    for y in _periods(occupancy):
        rows = [o for o in occupancy if o["dimensions"].get("TIME_PERIOD") == y]

        def get(ocs: str, rows=rows):
            return _value(next((o for o in rows if o["dimensions"].get("OCS") == ocs), None))

        total = get("_T")
        if not total:
            continue
        year = _year(y)
        secondary = get("DW_SEC_DW_OCC")
        vacant = get("DW_VAC")
        out.append({"inseeCode": insee, "indicator": "dwellings_total", "year": year, "value": js_round(total), "unit": "logements", **stamp})
        if secondary is not None:
            out.append({"inseeCode": insee, "indicator": "secondary_homes", "year": year, "value": js_round(secondary), "unit": "logements", **stamp})
            out.append({"inseeCode": insee, "indicator": "share_secondary_homes", "year": year, "value": _round(secondary / total * 100), "unit": "%", **stamp})
        if vacant is not None:
            out.append({"inseeCode": insee, "indicator": "vacant_dwellings", "year": year, "value": js_round(vacant), "unit": "logements", **stamp})
            out.append({"inseeCode": insee, "indicator": "share_vacant_dwellings", "year": year, "value": _round(vacant / total * 100), "unit": "%", **stamp})

    for y in _periods(stay):
        rows = [o for o in stay if o["dimensions"].get("TIME_PERIOD") == y]

        def get2(measure: str, lstay: str, rows=rows):
            return _value(next(
                (o for o in rows if o["dimensions"].get("RP_MEASURE") == measure and o["dimensions"].get("L_STAY") == lstay), None
            ))

        dwellings = get2("DWELLINGS", "_T")
        years = get2("DWELLING_L_STAY", "_T")
        recent = get2("DWELLINGS", "Y_LT2")
        if not dwellings:
            continue
        year = _year(y)
        if years is not None:
            out.append({"inseeCode": insee, "indicator": "mean_length_of_stay", "year": year, "value": _round(years / dwellings, 1), "unit": "ans", **stamp})
        if recent is not None:
            out.append({"inseeCode": insee, "indicator": "share_moved_in_last_2_years", "year": year, "value": _round(recent / dwellings * 100), "unit": "%", **stamp})
    return out


def normalize_tax(r: dict, stamp: dict) -> dict | None:
    year = int_(r.get("exercice"))
    if not year or not r.get("insee_com"):
        return None
    return {
        "inseeCode": r["insee_com"],
        "year": year,
        "epciCode": str_(r.get("sirepci"), 9),
        "propertyTaxRate": num(r.get("taux_global_tfb")),
        "landTaxRate": num(r.get("taux_global_tfnb")),
        "wasteTaxRate": num(r.get("taux_plein_teom")),
        "housingTaxRate": num(r.get("taux_global_th")),
        "secondaryHomeSurcharge": bool_from_flag(r.get("ind_majothrs")),
        "secondaryHomeSurchargeRate": num(r.get("thsurtaxrstau")),
        **stamp,
    }


def normalize_crime(r: dict, insee: str, stamp: dict) -> dict | None:
    year = int_(r.get("annee"))
    if not year or not r.get("indicateur"):
        return None
    return {
        "inseeCode": insee,
        "year": year,
        "indicator": str_(r["indicateur"], 128),
        "countUnit": str_(r.get("unite_de_compte"), 32),
        "count": int_(r.get("nombre")),
        "ratePerThousand": num(r.get("taux_pour_mille")),
        "isPublished": r.get("est_diffuse") == "diff",
        **stamp,
    }


# Tranches d'âge publiées telles quelles (effectif et part de la population).
AGE_BRACKET_INDICATORS = {
    "Y_LT15": "age_0_14", "Y15T24": "age_15_24", "Y25T39": "age_25_39", "Y40T54": "age_40_54",
    "Y55T64": "age_55_64", "Y65T79": "age_65_79", "Y_GE80": "age_80_plus",
}


def _row(insee: str, indicator: str, year, value, unit: str | None, stamp: dict) -> dict:
    return {"inseeCode": insee, "indicator": indicator, "year": year, "value": value, "unit": unit, **stamp}


def age_bracket_indicators(obs: list[dict], insee: str, stamp: dict) -> list[dict]:
    """Effectif et part de chaque tranche d'âge du recensement, par année."""
    out: list[dict] = []
    for y in _periods(obs):
        by_age = {
            o["dimensions"].get("AGE"): _value(o)
            for o in obs
            if o["dimensions"].get("TIME_PERIOD") == y and o["dimensions"].get("SEX") == "_T"
        }
        total = by_age.get("_T")
        if not total:
            continue
        for code, name in AGE_BRACKET_INDICATORS.items():
            n = by_age.get(code)
            if n is not None:
                out.append(_row(insee, name, _year(y), js_round(n), "habitants", stamp))
                out.append(_row(insee, f"share_{name}", _year(y), _round(n / total * 100), "%", stamp))
    return out


def population_history_indicators(obs: list[dict], insee: str, stamp: dict) -> list[dict]:
    """
    Population de chaque recensement depuis 1968 (DS_POPULATIONS_HISTORIQUES) : population municipale (PMUN),
    à défaut population sans doubles comptes (PSDC), seule publiée pour les recensements de 1968 à 1999.
    """
    by_year: dict = {}
    for measure in ("PSDC", "PMUN"):
        for o in obs:
            if o["dimensions"].get("POPREF_MEASURE") == measure and _value(o) is not None:
                by_year[_year(o["dimensions"].get("TIME_PERIOD"))] = js_round(_value(o))
    return [_row(insee, "municipal_population", year, value, "habitants", stamp) for year, value in sorted(by_year.items())]


def employment_indicators(obs: list[dict], insee: str, stamp: dict) -> list[dict]:
    """
    Actifs, emploi et chômage des 15-64 ans au sens du recensement (DS_RP_EMPLOI_LR_PRINC).
    EMPSTA_ENQ : 1 = actifs ayant un emploi, 2 = chômeurs, 1T2 = actifs, _T = ensemble des 15-64 ans.
    """
    out: list[dict] = []
    for y in _periods(obs):
        by_status = {o["dimensions"].get("EMPSTA_ENQ"): _value(o) for o in obs if o["dimensions"].get("TIME_PERIOD") == y}
        total, active, employed, unemployed = (by_status.get(k) for k in ("_T", "1T2", "1", "2"))
        year = _year(y)
        counts = (("active_population_15_64", active), ("employed_15_64", employed), ("unemployed_15_64", unemployed))
        out.extend(_row(insee, name, year, js_round(n), "personnes", stamp) for name, n in counts if n is not None)
        if active and unemployed is not None:
            out.append(_row(insee, "unemployment_rate", year, _round(unemployed / active * 100), "%", stamp))
        if total and active is not None:
            out.append(_row(insee, "activity_rate", year, _round(active / total * 100), "%", stamp))
        if total and employed is not None:
            out.append(_row(insee, "employment_rate", year, _round(employed / total * 100), "%", stamp))
    return out


# Mesures Filosofi retenues : indicateur, unité, nombre de décimales.
FILOSOFI_MEASURES = {
    "MED_SL": ("median_living_standard", "€/an", 0),
    "D1_SL": ("living_standard_d1", "€/an", 0),
    "D9_SL": ("living_standard_d9", "€/an", 0),
    "PR_MD60": ("poverty_rate", "%", 1),
    "GI_SL": ("gini_index", None, 3),
    "IR_D9_D1_SL": ("interdecile_ratio", None, 2),
    "S_SOC_BEN_DI": ("share_social_benefits", "%", 1),
    "S_RET_PEN_DI": ("share_pensions", "%", 1),
}


def income_indicators(obs: list[dict], insee: str, stamp: dict) -> list[dict]:
    """Niveau de vie, pauvreté et inégalités (Filosofi, DS_FILOSOFI_CC). Les valeurs sous secret statistique sont absentes."""
    out = []
    for o in obs:
        spec = FILOSOFI_MEASURES.get(o["dimensions"].get("FILOSOFI_MEASURE"))
        value = _value(o)
        if spec and value is not None:
            indicator, unit, digits = spec
            out.append(_row(insee, indicator, _year(o["dimensions"].get("TIME_PERIOD")), _round(value, digits), unit, stamp))
    return out
