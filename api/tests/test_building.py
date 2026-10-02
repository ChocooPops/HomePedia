from datetime import datetime

from app.modules.building.normalizers import building_presumptions, compute_price_index, normalize_dvf_row

stamp = {"sourceCode": "dvf", "fetchedAt": datetime.now(), "expiresAt": datetime.now()}


def sale(mutation_id: str, type_: str, price: float, area: int, date: str = "2024-03-01") -> dict:
    return {
        "mutationId": mutation_id, "mutationDate": date, "nature": "Vente", "propertyType": type_,
        "priceEur": price, "builtAreaM2": area, "inseeCode": "80021",
    }


def test_compute_price_index_ne_garde_que_les_ventes_a_un_seul_logement_et_ecarte_les_valeurs_aberrantes():
    rows = [
        sale("m1", "Appartement", 200000, 100),  # 2 000 €/m²
        sale("m2", "Appartement", 300000, 100),  # 3 000 €/m²
        sale("m3", "Maison", 250000, 100),
        sale("m4", "Appartement", 100000, 50),  # vente de 2 logements : ignorée
        sale("m4", "Appartement", 100000, 50),
        sale("m5", "Appartement", 10, 100),  # 0,1 €/m² : aberrant
        sale("m6", "Dépendance", 5000, 10),  # pas un logement
    ]
    index = compute_price_index(rows)
    appart = next(i for i in index if i["propertyType"] == "Appartement")
    assert appart["salesCount"] == 2
    assert appart["medianPriceM2"] == 2500
    ensemble = next(i for i in index if i["propertyType"] == "Ensemble")
    assert ensemble["salesCount"] == 3


def test_normalize_dvf_row_produit_un_hachage_stable_et_ignore_les_lignes_incompletes():
    row = {
        "id_mutation": "2024-1", "date_mutation": "2024-01-03", "nature_mutation": "Vente", "valeur_fonciere": "88000",
        "code_commune": "80021", "type_local": "Appartement", "surface_reelle_bati": "57",
    }
    a = normalize_dvf_row(row, stamp)
    b = normalize_dvf_row({**row}, stamp)
    assert len(a["rowHash"]) == 40
    assert a["rowHash"] == b["rowHash"]
    assert a["priceEur"] == 88000
    assert normalize_dvf_row({**row, "id_mutation": ""}, stamp) is None


NOW = datetime(2026, 10, 2)


def _matches(actual: dict, expected: dict) -> bool:
    return all(actual[k] == v and type(actual[k]) is type(v) for k, v in expected.items())


def test_building_presumptions_applique_les_seuils_plomb_amiante():
    assert _matches(building_presumptions(1930, None, NOW), {"leadRisk": True, "asbestosRisk": True})
    assert _matches(building_presumptions(1980, None, NOW), {"leadRisk": False, "asbestosRisk": True})
    assert _matches(building_presumptions(2005, None, NOW), {"leadRisk": False, "asbestosRisk": False})
    assert building_presumptions(None, None, NOW)["leadRisk"] is None


def test_building_presumptions_suit_le_calendrier_d_interdiction_de_location():
    assert _matches(building_presumptions(1970, "G", NOW), {"rentalBanned": True, "rentalBanDate": "2025-01-01"})
    assert _matches(building_presumptions(1970, "F", NOW), {"rentalBanned": False, "rentalBanDate": "2028-01-01"})
    assert _matches(building_presumptions(1970, "C", NOW), {"rentalBanned": False, "rentalBanDate": None})
