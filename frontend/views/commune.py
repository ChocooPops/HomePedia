import re

import pandas as pd
import streamlit as st

from lib import api, charts, ui

st.title("Fiche commune")

# ----------------------------------------------------------------- Choix de la commune
departments = api.try_get("/departments", [])
department_names = {d["code"]: f"{d['code']} – {d['name']}" for d in departments}
f_dep, f_commune, f_code = st.columns([2, 3, 1.2])
# Lien direct vers une fiche : ?insee=80021
insee = st.query_params.get("insee") or st.session_state.get("insee")
current_dep = (insee[:3] if insee and insee.startswith("97") else insee[:2]) if insee else st.session_state.get("department")
dep = f_dep.selectbox(
    "Département", list(department_names), format_func=department_names.get,
    index=list(department_names).index(current_dep) if current_dep in department_names else None,
    placeholder="Choisir un département",
) if department_names else None
communes = api.try_get("/communes", {"items": []}, department=dep, limit=500).get("items", []) if dep else []
if dep and len(communes) == 500:
    communes += api.try_get("/communes", {"items": []}, department=dep, limit=500, page=2).get("items", [])
commune_names = {c["inseeCode"]: f"{c['name']} ({c['inseeCode']})" for c in sorted(communes, key=lambda c: c["name"])}
picked = f_commune.selectbox(
    "Commune", list(commune_names), format_func=commune_names.get,
    index=list(commune_names).index(insee) if insee in commune_names else None,
    placeholder="Choisir une commune" if commune_names else "Aucune commune chargée pour ce département",
)
typed = f_code.text_input("ou code INSEE", value="", max_chars=5, placeholder="80021")
if typed and re.fullmatch(r"\d{5}|2[AB]\d{3}", typed):
    insee = typed
elif picked:
    insee = picked
if dep and not communes:
    if st.button(f"Charger les communes du département {dep}"):
        if ui.run("Chargement des communes", lambda: api.post(f"/departments/{dep}/communes/collect")):
            st.rerun()
if not insee:
    st.info("Choisir une commune pour afficher sa fiche.")
    st.stop()
st.session_state["insee"] = insee

report = api.try_get(f"/communes/{insee}/report")
indicators = ((report or {}).get("socio") or {}).get("demography", {}).get("latest", {})

action, status = st.columns([1, 3], vertical_alignment="center")
if action.button("Collecter les données" if not indicators else "Actualiser les données", type="primary" if not indicators else "secondary"):
    result = ui.run(
        "Collecte de la commune : recensement, emploi, revenus, ventes DVF, énergie (jusqu’à une minute)",
        lambda: api.post(f"/communes/{insee}/collect-all"),
    )
    if result:
        st.session_state["commune_collect"] = result
        st.rerun()
if last := st.session_state.pop("commune_collect", None):
    status.success(ui.collect_summary(last["summary"]))
    with st.expander("Détail de la collecte"):
        ui.outcomes_table(last["outcomes"])
if not report:
    st.warning("Cette commune n’a pas encore été collectée.")
    st.stop()

commune = report["commune"]
series = report["socio"]["demography"]["series"]
st.header(commune["name"])
st.caption(
    f"{commune.get('departmentName') or ''} ({commune['departmentCode']}), {commune.get('regionName') or ''} · "
    f"codes postaux {', '.join(commune.get('postalCodes') or [])} · {ui.number(commune.get('surfaceHa'))} ha"
)
if not indicators:
    st.warning("Les indicateurs de la commune ne sont pas encore collectés : utiliser « Collecter les données ».")
    st.stop()


def frame(indicator_names: dict[str, str]) -> pd.DataFrame:
    """Séries d'indicateurs au format long : année, série, valeur."""
    rows = [
        {"Année": point["year"], "Série": label, "Valeur": point["value"]}
        for key, label in indicator_names.items()
        for point in series.get(key, [])
    ]
    return pd.DataFrame(rows)


# ----------------------------------------------------------------- Chiffres clés
price_index = report["market"]["priceIndex"]
overall = [p for p in price_index if p["propertyType"] == "Ensemble"]
last_price = overall[-1] if overall else None

row = [*st.columns(3), *st.columns(3)]
value, year = ui.latest(indicators, "municipal_population")
if value is None:
    value, year = ui.latest(indicators, "population")
ui.tile(row[0], "Population", ui.number(value), f"recensement {year}" if year else None)
value, year = ui.latest(indicators, "median_living_standard")
ui.tile(row[1], "Niveau de vie médian", ui.euro(value), f"par an et par unité de consommation, {year}" if year else None)
value, year = ui.latest(indicators, "poverty_rate")
ui.tile(row[2], "Taux de pauvreté", ui.pct(value), f"seuil à 60 %, {year}" if year else None)
value, year = ui.latest(indicators, "unemployment_rate")
ui.tile(row[3], "Chômage", ui.pct(value), f"15-64 ans, au sens du recensement {year}" if year else None)
value, year = ui.latest(indicators, "share_vacant_dwellings")
ui.tile(row[4], "Logements vacants", ui.pct(value), f"part du parc, {year}" if year else None)
ui.tile(
    row[5], "Prix médian",
    ui.euro(last_price["medianPriceM2"]) + "/m²" if last_price else "n.d.",
    f"{ui.number(last_price['salesCount'])} ventes en {last_price['year']}" if last_price else "aucune vente DVF chargée",
)

tabs = st.tabs(["Démographie", "Emploi et revenus", "Logement", "Marché immobilier", "Énergie", "Fiscalité et sécurité", "Risques", "Avis"])

# ----------------------------------------------------------------- Démographie
with tabs[0]:
    left, right = st.columns(2)
    with left:
        st.subheader("Population municipale depuis 1968")
        charts.line(frame({"municipal_population": "Population"}), "Année", "Valeur", y_title="Habitants")
        st.caption("Source : INSEE, populations municipales historiques.")
    with right:
        st.subheader("Répartition par âge")
        brackets = {
            "share_age_0_14": "0-14", "share_age_15_24": "15-24", "share_age_25_39": "25-39", "share_age_40_54": "40-54",
            "share_age_55_64": "55-64", "share_age_65_79": "65-79", "share_age_80_plus": "80 et +",
        }
        ages = pd.DataFrame([
            {"Tranche": label, "Part": indicators[key]["value"]} for key, label in brackets.items() if key in indicators
        ])
        charts.bars(
            ages, "Tranche", "Part", category_title="Âge (ans)", value_title="Part de la population (%)", value_format=",.1f",
            sort=list(brackets.values()),
        )
        mean_age, year = ui.latest(indicators, "mean_age_estimated")
        st.caption(f"Recensement {year}. Âge moyen estimé : {ui.number(mean_age, 1)} ans. Source : INSEE." if year else "Source : INSEE.")

# ----------------------------------------------------------------- Emploi et revenus
with tabs[1]:
    row = st.columns(4)
    for column, (key, label, digits, unit) in zip(row, (
        ("activity_rate", "Taux d’activité", 1, "%"),
        ("employment_rate", "Taux d’emploi", 1, "%"),
        ("unemployment_rate", "Taux de chômage", 1, "%"),
        ("active_population_15_64", "Actifs de 15 à 64 ans", 0, ""),
    ), strict=True):
        value, year = ui.latest(indicators, key)
        ui.tile(column, label, ui.number(value, digits, unit), f"recensement {year}" if year else None)
    left, right = st.columns(2)
    with left:
        st.subheader("Activité, emploi et chômage")
        charts.line(
            frame({"activity_rate": "Taux d’activité", "employment_rate": "Taux d’emploi", "unemployment_rate": "Taux de chômage"}),
            "Année", "Valeur", series="Série", y_title="% des 15-64 ans (chômage : % des actifs)", y_format=",.1f", zero=True,
        )
        st.caption("Chômage au sens du recensement (déclaratif), supérieur au taux du BIT. Source : INSEE.")
    with right:
        st.subheader("Niveau de vie")
        income = [
            ("living_standard_d1", "1er décile (les 10 % les plus modestes)", ui.euro),
            ("median_living_standard", "Médiane", ui.euro),
            ("living_standard_d9", "9e décile (les 10 % les plus aisés)", ui.euro),
            ("interdecile_ratio", "Rapport interdécile (D9 / D1)", lambda v: ui.number(v, 2)),
            ("gini_index", "Indice de Gini", lambda v: ui.number(v, 3)),
            ("share_social_benefits", "Part des prestations sociales", ui.pct),
            ("share_pensions", "Part des pensions et retraites", ui.pct),
        ]
        rows = [
            {"Indicateur": label, "Valeur": fmt(indicators[key]["value"]), "Année": indicators[key]["year"]}
            for key, label, fmt in income
            if key in indicators
        ]
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        else:
            st.info("Aucune donnée Filosofi pour cette commune.")
        st.caption("Les mesures absentes sont couvertes par le secret statistique. Source : INSEE, Filosofi.")

# ----------------------------------------------------------------- Logement
with tabs[2]:
    row = st.columns(4)
    for column, (key, label, digits, unit) in zip(row, (
        ("dwellings_total", "Logements", 0, ""),
        ("share_vacant_dwellings", "Logements vacants", 1, "%"),
        ("share_secondary_homes", "Résidences secondaires", 1, "%"),
        ("mean_length_of_stay", "Ancienneté moyenne d’occupation", 1, "ans"),
    ), strict=True):
        value, year = ui.latest(indicators, key)
        ui.tile(column, label, ui.number(value, digits, unit), f"recensement {year}" if year else None)
    st.subheader("Vacance et résidences secondaires")
    charts.line(
        frame({"share_vacant_dwellings": "Logements vacants", "share_secondary_homes": "Résidences secondaires"}),
        "Année", "Valeur", series="Série", y_title="Part du parc de logements (%)", y_format=",.1f", zero=True,
    )
    moved, year = ui.latest(indicators, "share_moved_in_last_2_years")
    st.caption(
        (f"{ui.pct(moved)} des ménages ont emménagé depuis moins de 2 ans ({year}). " if moved is not None else "")
        + "Source : INSEE, recensement de la population."
    )

# ----------------------------------------------------------------- Marché
with tabs[3]:
    if not price_index:
        st.info("Aucune vente DVF chargée pour cette commune.")
    else:
        types = ["Ensemble", "Appartement", "Maison"]
        df = pd.DataFrame(price_index)
        df = df[df["propertyType"].isin(types)].rename(
            columns={"year": "Année", "propertyType": "Type", "medianPriceM2": "Prix médian", "salesCount": "Ventes"}
        )
        left, right = st.columns(2)
        with left:
            st.subheader("Prix médian au m²")
            charts.line(df, "Année", "Prix médian", series="Type", order=types, y_title="€/m²")
        with right:
            st.subheader("Nombre de ventes")
            charts.bars(
                df[df["Type"] != "Ensemble"], "Année", "Ventes", series="Type", order=types, value_title="Ventes retenues"
            )
        st.caption(
            "Ventes d’un seul logement par mutation, prix hors de 200 à 30 000 €/m² écartés. "
            "La dernière année est incomplète tant que les actes ne sont pas tous publiés. Source : DVF (DGFiP)."
        )
        ui.table(price_index[::-1], {
            "year": "Année", "propertyType": "Type", "salesCount": "Ventes", "q1PriceM2": "1er quartile €/m²",
            "medianPriceM2": "Médiane €/m²", "q3PriceM2": "3e quartile €/m²", "meanPriceM2": "Moyenne €/m²",
        }, height=260)
    listing_stats = report["market"]["listings"]
    st.subheader("Annonces en ligne")
    if listing_stats["groups"]:
        ui.table(listing_stats["groups"], {
            "transactionType": "Transaction", "propertyType": "Bien", "listingsCount": "Annonces",
            "medianPriceM2": "Médiane €/m²", "avgPriceM2": "Moyenne €/m²", "minPriceM2": "Minimum", "maxPriceM2": "Maximum",
        })
    else:
        st.caption("Aucune annonce remontée par le scraping pour cette commune.")

# ----------------------------------------------------------------- Énergie
with tabs[4]:
    energy = report["energy"]
    if not energy["bySector"]:
        st.info("Consommations d’énergie non collectées pour cette commune.")
    else:
        totals = pd.DataFrame(energy["totalsByYear"])
        totals["Énergie"] = totals["energy"].map(ui.ENERGIES)
        totals["GWh"] = totals["consumptionMwh"] / 1000
        totals = totals.rename(columns={"year": "Année"})
        left, right = st.columns(2)
        with left:
            st.subheader("Consommation annuelle")
            charts.line(totals, "Année", "GWh", series="Énergie", order=list(ui.ENERGIES.values()), y_title="GWh", zero=True)
        with right:
            st.subheader(f"Répartition par secteur en {energy['latestYear']}")
            sectors = pd.DataFrame(energy["latest"])
            sectors["Énergie"] = sectors["energy"].map(ui.ENERGIES)
            sectors["Secteur"] = sectors["sector"].map(lambda s: ui.SECTORS.get(s, s.capitalize()))
            sectors["GWh"] = sectors["consumptionMwh"] / 1000
            largest_first = list(sectors.groupby("Secteur")["GWh"].sum().sort_values(ascending=False).index)
            charts.bars(
                sectors, "Secteur", "GWh", series="Énergie", order=list(ui.ENERGIES.values()), horizontal=True,
                stacked=False, value_title="GWh", value_format=",.1f", sort=largest_first,
            )
        st.caption("Électricité et gaz livrés sur les réseaux de distribution, tous secteurs. Source : Agence ORE.")

# ----------------------------------------------------------------- Fiscalité et sécurité
with tabs[5]:
    taxes = report["socio"]["taxes"]
    left, right = st.columns(2)
    with left:
        st.subheader("Taux d’imposition locale")
        ui.table(taxes["history"][::-1], {
            "year": "Année", "propertyTaxRate": "Taxe foncière (bâti) %", "landTaxRate": "Taxe foncière (non bâti) %",
            "wasteTaxRate": "Ordures ménagères %", "housingTaxRate": "Taxe d’habitation %",
        })
        change = taxes.get("propertyTaxRateChange")
        if change:
            st.caption(
                f"Taxe foncière sur le bâti : {'+' if change['points'] >= 0 else ''}{ui.number(change['points'], 2)} point "
                f"entre {change['from']} et {change['to']}. Source : DGFiP."
            )
    with right:
        crime = report["socio"]["crime"]
        st.subheader(f"Délinquance enregistrée en {crime['year']}" if crime["year"] else "Délinquance enregistrée")
        ui.table(crime["highlights"], {
            "indicator": "Indicateur", "count": "Faits", "countUnit": "Unité", "ratePerThousand": "Pour 1 000 habitants",
        }, config={"Pour 1 000 habitants": st.column_config.NumberColumn(format="%.1f")})
        st.caption("Faits enregistrés par la police et la gendarmerie. Source : SSMSI.")

# ----------------------------------------------------------------- Risques
with tabs[6]:
    profile = report["risks"]["profile"]
    catnat = report["risks"]["catnat"]
    if not profile and not catnat:
        st.info("Les risques sont collectés lors de l’analyse d’une adresse de la commune (Géorisques).")
    else:
        row = st.columns(3)
        ui.tile(row[0], "Potentiel radon", f"classe {profile['radonClass']}" if profile and profile.get("radonClass") else "n.d.", "de 1 (faible) à 3 (significatif)")
        ui.tile(row[1], "Zone de sismicité", (profile or {}).get("seismicZone") or "n.d.")
        ui.tile(row[2], "Arrêtés de catastrophe naturelle", ui.number(len(catnat)))
        if profile and profile.get("knownRisks"):
            st.write("Risques recensés sur la commune : " + ", ".join(profile["knownRisks"]) + ".")
        ui.table(catnat, {
            "hazardLabel": "Aléa", "eventStart": "Début", "eventEnd": "Fin", "decreeDate": "Arrêté", "journalDate": "Journal officiel",
        }, height=300)
        st.caption("Source : Géorisques (base GASPAR).")

# ----------------------------------------------------------------- Avis
with tabs[7]:
    summary = report["reviews"]
    if not summary["total"]:
        st.info("Aucun avis pour cette commune. Les imports se font depuis la page « Avis ».")
    else:
        ui.table(summary["groups"], {
            "source": "Source", "kind": "Type", "reviewsCount": "Avis", "subjectsCount": "Lieux ou quartiers", "avgRating": "Note moyenne / 5",
        })
        reviews = api.try_get("/reviews", {"items": []}, insee=insee, limit=20)["items"]
        for review in reviews:
            rating = f"{ui.number(review['rating'], 1)} / 5" if review.get("rating") is not None else "sans note"
            st.markdown(f"**{review.get('subjectName', '')}** · {rating}")
            if review.get("text"):
                st.write(review["text"])
            st.caption(" · ".join(x for x in (review.get("author"), (review.get("publishedAt") or "")[:10], review["source"]) if x))
