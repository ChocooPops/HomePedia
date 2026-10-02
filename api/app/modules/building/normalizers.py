"""Transformation des réponses brutes en lignes de la base (fonctions pures, testables)."""

import hashlib
from datetime import datetime

from ...geo_utils import geojson_to_wkt, point_wkt
from ...parse import bool_from_flag, int_, iso_date, js_round, num, quantile, str_, utcnow


def normalize_rnb(b: dict, insee: str | None, stamp: dict) -> dict:
    lon, lat = b["point"]["coordinates"][:2]
    addresses = b.get("addresses") or []
    address_insee = addresses[0].get("city_insee_code") if addresses and addresses[0] else None
    return {
        "rnbId": b["rnb_id"],
        "status": str_(b.get("status"), 24),
        "inseeCode": address_insee if address_insee is not None else insee,
        "latitude": lat,
        "longitude": lon,
        "location": point_wkt(lon, lat),
        "shape": geojson_to_wkt(b["shape"]) if b.get("shape") else None,
        **stamp,
    }


def normalize_bdnb(g: dict) -> dict:
    """Enrichissement BDNB (champs descriptifs du groupe de bâtiments)."""
    row = {
        "bdnbGroupId": g.get("batiment_groupe_id"),
        "inseeCode": g.get("code_commune_insee"),
        "constructionYear": int_(g.get("annee_construction")),
        "heightM": num(g.get("hauteur_mean")),
        "levels": int_(g.get("nb_niveau")),
        "dwellings": int_(g.get("nb_log")),
        "wallMaterial": str_(g.get("mat_mur_txt"), 80),
        "roofMaterial": str_(g.get("mat_toit_txt"), 80),
        "mainUsage": str_(g.get("usage_niveau_1_txt"), 80),
        "dpeClassBdnb": str_(g.get("classe_bilan_dpe"), 1),
        "condoRegistration": str_(g.get("numero_immat_principal"), 16),
        "irisCode": str_(g.get("code_iris"), 9),
        "footprintM2": int_(g.get("surface_emprise_sol")),
        "groundAltitudeM": num(g.get("altitude_sol_mean")),
    }
    # Sans commune côté BDNB, on garde celle déjà connue (clé omise : colonne non mise à jour).
    if row["inseeCode"] is None:
        del row["inseeCode"]
    return row


def normalize_dpe(d: dict, stamp: dict) -> dict:
    geopoint = d.get("_geopoint")
    coords = [num(x) for x in str(geopoint if geopoint is not None else "").split(",")]
    return {
        "numeroDpe": d["numero_dpe"],
        "rnbId": str_(d.get("id_rnb"), 12),
        "banId": str_(d.get("identifiant_ban"), 64),
        "addressLabel": str_(d.get("adresse_ban"), 255),
        "inseeCode": str_(d.get("code_insee_ban"), 5),
        "issuedAt": iso_date(d.get("date_etablissement_dpe")),
        "energyClass": str_(d.get("etiquette_dpe"), 1),
        "ghgClass": str_(d.get("etiquette_ges"), 1),
        "energyKwhM2": num(d.get("conso_5_usages_par_m2_ep")),
        "ghgKgM2": num(d.get("emission_ges_5_usages_par_m2")),
        "constructionYear": int_(d.get("annee_construction")),
        "constructionPeriod": str_(d.get("periode_construction"), 24),
        "buildingType": str_(d.get("type_batiment"), 24),
        "livingAreaM2": num(d.get("surface_habitable_logement")),
        "ceilingHeightM": num(d.get("hauteur_sous_plafond")),
        "heatingEnergy": str_(d.get("type_energie_principale_chauffage"), 80),
        "annualCostEur": num(d.get("cout_total_5_usages")),
        "latitude": coords[0],
        "longitude": coords[1] if len(coords) > 1 else None,
        **stamp,
    }


def normalize_dvf_row(r: dict[str, str], stamp: dict) -> dict | None:
    if not r.get("id_mutation") or not r.get("date_mutation") or not r.get("code_commune"):
        return None
    address = " ".join(
        part
        for part in (r.get(k) for k in ("adresse_numero", "adresse_suffixe", "adresse_nom_voie", "code_postal", "nom_commune"))
        if part
    )
    return {
        # Une ligne DVF n'a pas d'identifiant propre : on hache son contenu pour dédoublonner les imports.
        "rowHash": hashlib.sha1("|".join("" if v is None else str(v) for v in r.values()).encode("utf-8")).hexdigest(),
        "mutationId": r["id_mutation"],
        "mutationDate": r["date_mutation"],
        "nature": r.get("nature_mutation"),
        "priceEur": num(r.get("valeur_fonciere")),
        "inseeCode": r["code_commune"],
        "parcelIdu": str_(r.get("id_parcelle"), 14),
        "addressLabel": str_(address, 255),
        "propertyType": str_(r.get("type_local"), 48),
        "builtAreaM2": int_(r.get("surface_reelle_bati")),
        "rooms": int_(r.get("nombre_pieces_principales")),
        "landAreaM2": int_(r.get("surface_terrain")),
        "lotsCount": int_(r.get("nombre_lots")),
        "latitude": num(r.get("latitude")),
        "longitude": num(r.get("longitude")),
        **stamp,
    }


def normalize_rnic(r: dict, stamp: dict) -> dict:
    refs = [x for x in (str_(r.get(f"reference_cadastrale_{i}")) for i in (1, 2, 3)) if x]
    commune = r.get("code_officiel_commune")
    return {
        "registrationNumber": r["numero_d_immatriculation"],
        "name": str_(r.get("nom_d_usage_de_la_copropriete"), 255),
        "addressLabel": str_(r.get("adresse_de_reference"), 255),
        "inseeCode": str_(commune if commune is not None else r.get("commune"), 5),
        "totalLots": int_(r.get("nombre_total_de_lots")),
        "housingLots": int_(r.get("nombre_de_lots_a_usage_d_habitation")),
        "parkingLots": int_(r.get("nombre_de_lots_de_stationnement")),
        "syndicType": str_(r.get("type_de_syndic_benevole_professionnel_non_connu"), 32),
        "syndicName": str_(r.get("raison_sociale_du_representant_legal"), 255),
        "mandateStatus": str_(r.get("mandat_en_cours_dans_la_copropriete"), 64),
        "mandateEndDate": iso_date(r.get("date_de_fin_du_dernier_mandat")),
        "constructionPeriod": str_(r.get("periode_de_construction"), 32),
        "regulationDate": iso_date(r.get("date_du_reglement_de_copropriete")),
        "isAided": bool_from_flag(r.get("copro_aidee")),
        "priorityDistrict": str_(r.get("nom_qp_2024"), 120),
        "cadastralRefs": refs,
        "latitude": num(r.get("lat")),
        "longitude": num(r.get("long")),
        **stamp,
    }


def _round2(v: float | None) -> float | None:
    return None if v is None else js_round(v * 100) / 100


def compute_price_index(rows: list[dict], computed_at: datetime | None = None) -> list[dict]:
    """
    Prix au m² par commune / année / type, à partir des ventes « simples » :
    une mutation de type Vente comportant exactement un local Maison ou Appartement.
    Valeurs hors [200 ; 30 000] €/m² écartées (erreurs de saisie, ventes en bloc).
    """
    computed_at = computed_at or utcnow()
    by_mutation: dict[str, list[dict]] = {}
    for r in rows:
        if r.get("nature") != "Vente":
            continue
        by_mutation.setdefault(r["mutationId"], []).append(r)

    buckets: dict[str, dict] = {}
    for lines in by_mutation.values():
        dwellings = [line for line in lines if line.get("propertyType") in ("Maison", "Appartement")]
        if len(dwellings) != 1:
            continue
        d = dwellings[0]
        if not d.get("priceEur") or not d.get("builtAreaM2"):
            continue
        m2 = d["priceEur"] / d["builtAreaM2"]
        if m2 < 200 or m2 > 30000:
            continue
        year = int(str(d["mutationDate"])[:4])
        for type_ in (d["propertyType"], "Ensemble"):
            key = f"{d['inseeCode']}|{year}|{type_}"
            b = buckets.setdefault(key, {"insee": d["inseeCode"], "year": year, "type": type_, "values": []})
            b["values"].append(m2)

    index = []
    for b in buckets.values():
        values = sorted(b["values"])
        # Somme dans l'ordre, sans compensation des arrondis : les moyennes restent identiques d'un recalcul à l'autre.
        total = 0.0
        for v in values:
            total += v
        index.append({
            "inseeCode": b["insee"],
            "year": b["year"],
            "propertyType": b["type"],
            "salesCount": len(values),
            "medianPriceM2": _round2(quantile(values, 0.5)),
            "meanPriceM2": _round2(total / len(values)),
            "q1PriceM2": _round2(quantile(values, 0.25)),
            "q3PriceM2": _round2(quantile(values, 0.75)),
            "computedAt": computed_at,
        })
    return index


# Calendrier légal d'interdiction de mise en location (loi Climat et résilience).
RENTAL_BAN_DATES: dict[str, str] = {"G": "2025-01-01", "F": "2028-01-01", "E": "2034-01-01"}


def building_presumptions(year: int | None, energy_class: str | None, now: datetime | None = None) -> dict:
    """Présomptions réglementaires liées à l'année de construction (pas un diagnostic)."""
    now = now or utcnow()
    ban = RENTAL_BAN_DATES.get(energy_class) if energy_class else None
    return {
        "leadRisk": None if year is None else year < 1949,
        "asbestosRisk": None if year is None else year < 1997,
        "rentalBanDate": ban,
        "rentalBanned": datetime.fromisoformat(ban) <= now if ban else False,
        "notes": [
            "Plomb : constat (CREP) obligatoire pour les logements construits avant le 01/01/1949.",
            "Amiante : repérage obligatoire si le permis de construire est antérieur au 01/07/1997.",
        ],
    }
