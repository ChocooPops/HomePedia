"""Normaliseurs des sources ajoutées pour l'analyse de territoire : Melodi (emploi, revenus, historique), Agence ORE, avis."""

from datetime import datetime

from app.modules.energy.ore import normalize_consumption
from app.modules.reviews.service import normalize_imported_review, normalize_place_reviews
from app.modules.socio.normalizers import (
    age_bracket_indicators,
    employment_indicators,
    income_indicators,
    population_history_indicators,
)
from app.modules.territory.service import department_of

STAMP = {"sourceCode": "test", "fetchedAt": datetime(2026, 1, 1), "expiresAt": datetime(2026, 2, 1)}


def obs(value, **dimensions):
    return {"dimensions": {"TIME_PERIOD": "2023", **dimensions}, "measures": {"OBS_VALUE_NIVEAU": {"value": value}}}


def by_indicator(rows):
    return {r["indicator"]: r["value"] for r in rows}


def test_tranches_d_age_en_effectif_et_en_part():
    rows = age_bracket_indicators(
        [obs(1000, SEX="_T", AGE="_T"), obs(180, SEX="_T", AGE="Y_LT15"), obs(90, SEX="_T", AGE="Y_GE80"), obs(99, SEX="F", AGE="Y_LT15")],
        "80021", STAMP,
    )
    values = by_indicator(rows)
    assert values == {"age_0_14": 180, "share_age_0_14": 18, "age_80_plus": 90, "share_age_80_plus": 9}
    assert {r["year"] for r in rows} == {2023}


def test_population_historique_prefere_la_population_municipale():
    rows = population_history_indicators(
        [obs(132699.0, TIME_PERIOD="2013", POPREF_MEASURE="PMUN"), obs(140000, TIME_PERIOD="2013", POPREF_MEASURE="PSDC"),
         obs(117888, TIME_PERIOD="1968", POPREF_MEASURE="PSDC")],
        "80021", STAMP,
    )
    assert [(r["year"], r["value"]) for r in rows] == [(1968, 117888), (2013, 132699)]


def test_taux_de_chomage_d_activite_et_d_emploi():
    rows = employment_indicators(
        [obs(1000, EMPSTA_ENQ="_T"), obs(700, EMPSTA_ENQ="1T2"), obs(595, EMPSTA_ENQ="1"), obs(105, EMPSTA_ENQ="2")], "80021", STAMP
    )
    values = by_indicator(rows)
    assert values["unemployment_rate"] == 15
    assert values["activity_rate"] == 70
    assert values["employment_rate"] == 59.5
    assert values["unemployed_15_64"] == 105


def test_filosofi_ignore_les_valeurs_sous_secret():
    rows = income_indicators(
        [obs(21340.4, FILOSOFI_MEASURE="MED_SL"), obs(21.26, FILOSOFI_MEASURE="PR_MD60"), obs(0.3149, FILOSOFI_MEASURE="GI_SL"),
         {"dimensions": {"TIME_PERIOD": "2023", "FILOSOFI_MEASURE": "IR_D9_D1_SL"}, "measures": {"OBS_VALUE_NIVEAU": {}}},
         obs(5, FILOSOFI_MEASURE="Q1_SL")],
        "80021", STAMP,
    )
    assert by_indicator(rows) == {"median_living_standard": 21340, "poverty_rate": 21.3, "gini_index": 0.315}


def test_ore_agrege_les_secteurs_naf_par_grand_secteur():
    rows = normalize_consumption(
        [
            {"annee": "2024", "filiere": "Electricité", "code_grand_secteur": "INDUSTRIE", "conso_totale_mwh": 3959.231, "nb_sites": 34},
            {"annee": "2024", "filiere": "Electricité", "code_grand_secteur": "INDUSTRIE", "conso_totale_mwh": 73.963, "nb_sites": 1},
            {"annee": "2024", "filiere": "Gaz", "code_grand_secteur": "RESIDENTIEL", "conso_totale_mwh": 100, "nb_sites": 10},
            {"annee": "2024", "filiere": "Chaleur", "code_grand_secteur": "RESIDENTIEL", "conso_totale_mwh": 1},
        ],
        "80021", STAMP,
    )
    assert [(r["energy"], r["sector"], r["sites"], r["consumptionMwh"]) for r in rows] == [
        ("electricity", "INDUSTRIE", 35, 4033.194),
        ("gas", "RESIDENTIEL", 10, 100),
    ]


def test_avis_importe_identifiant_stable_et_date_francaise():
    item = {"subject": "  Saint-Leu ", "rating": 4.5, "text": " Quartier vivant ", "date": "14/05/2026", "inseeCode": "80021"}
    a = normalize_imported_review("meilleursagents", "neighbourhood", item)
    b = normalize_imported_review("meilleursagents", "neighbourhood", dict(item))
    assert a["externalId"] == b["externalId"]
    assert a["subjectName"] == "Saint-Leu"
    assert a["text"] == "Quartier vivant"
    assert a["publishedAt"] == datetime(2026, 5, 14)
    assert "author" not in a


def test_avis_google_un_document_par_avis():
    place = {
        "id": "ChIJ1", "displayName": {"text": "Boulangerie"}, "rating": 4.4, "userRatingCount": 120,
        "location": {"latitude": 49.89, "longitude": 2.29},
        "reviews": [
            {"name": "places/ChIJ1/reviews/a", "rating": 5, "originalText": {"text": "Très bon pain", "languageCode": "fr"},
             "authorAttribution": {"displayName": "A."}, "publishTime": "2026-03-01T10:00:00Z"},
            {"rating": 2, "text": {"text": "Bof"}},
        ],
    }
    docs = normalize_place_reviews(place, {"inseeCode": "80021", "city": "Amiens", "postcode": "80000"})
    assert [d["externalId"] for d in docs] == ["places/ChIJ1/reviews/a", "ChIJ1:1"]
    assert docs[0]["text"] == "Très bon pain"
    assert docs[0]["publishedAt"] == datetime(2026, 3, 1, 10)
    assert docs[0]["location"] == {"type": "Point", "coordinates": [2.29, 49.89]}
    assert docs[1]["subjectRating"] == 4.4


def test_departement_d_une_commune():
    assert department_of("80021") == "80"
    assert department_of("2A004") == "2A"
    assert department_of("97411") == "974"
