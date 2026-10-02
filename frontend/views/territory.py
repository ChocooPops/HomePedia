import pandas as pd
import pydeck as pdk
import streamlit as st

from lib import api, charts, ui

st.title("Territoires")
st.caption("Prix au m² des ventes enregistrées (DVF), commune par commune, à l’échelle d’un département.")

regions = api.try_get("/regions", [])
if not regions:
    st.warning("Le référentiel territorial n’est pas chargé.")
    if st.button("Charger les régions et les départements"):
        if ui.run("Chargement du référentiel", lambda: api.post("/territories/collect")):
            st.rerun()
    st.stop()

# ----------------------------------------------------------------- Filtres (une seule rangée, au-dessus de la carte)
f_region, f_department, f_type, f_year = st.columns([2, 2, 1.4, 1])
region_names = {r["code"]: r["name"] for r in regions}
# Lien direct vers un département : ?dep=80
default_department = st.query_params.get("dep") or st.session_state.get("department")
region_of = {d["code"]: d["regionCode"] for d in api.try_get("/departments", [])}
default_region = region_of.get(default_department, "32")
region = f_region.selectbox(
    "Région", list(region_names), format_func=region_names.get,
    index=list(region_names).index(default_region) if default_region in region_names else 0,
)
departments = api.try_get("/departments", [], region=region)
department_names = {d["code"]: f"{d['code']} – {d['name']}" for d in departments}
if not department_names:
    st.info("Aucun département pour cette région.")
    st.stop()
dep = f_department.selectbox(
    "Département", list(department_names), format_func=department_names.get,
    index=list(department_names).index(default_department) if default_department in department_names else 0,
)
st.session_state["department"] = dep
property_type = f_type.selectbox("Type de bien", ["Ensemble", "Appartement", "Maison"])

prices = api.try_get(f"/departments/{dep}/prices", {"communes": [], "availableYears": [], "year": None}, type=property_type)
years = prices["availableYears"]
year = f_year.selectbox("Année", years[::-1]) if years else None
if year and year != prices["year"]:
    prices = api.get(f"/departments/{dep}/prices", type=property_type, year=year)

contours = api.try_get(f"/departments/{dep}/communes/contours", {"features": []})

# ----------------------------------------------------------------- Données manquantes : proposer la collecte
if not contours["features"] or not prices["communes"]:
    st.info(
        "Ce département n’a pas encore toutes ses données : contours des communes "
        f"({'chargés' if contours['features'] else 'absents'}), ventes DVF ({'chargées' if prices['communes'] else 'absentes'})."
    )
    if st.button(f"Charger le département {department_names[dep]}", type="primary"):
        results = []
        for label, path in (
            ("Communes du département", f"/departments/{dep}/communes/collect"),
            ("Contours des communes", f"/departments/{dep}/contours/collect"),
            ("Ventes DVF (dernière année publiée) et indices de prix", f"/departments/{dep}/dvf/collect"),
        ):
            result = ui.run(label, lambda path=path: api.post(path))
            if result is None:
                st.stop()
            results += result if isinstance(result, list) else [result]
        ui.outcomes_table(results)
        st.rerun()
    st.stop()

# ----------------------------------------------------------------- Chiffres clés
by_commune = {c["inseeCode"]: c for c in prices["communes"]}
medians = [c["medianPriceM2"] for c in prices["communes"] if c["medianPriceM2"] is not None]
sales = sum(c["salesCount"] for c in prices["communes"])
row = st.columns(4)
ui.tile(row[0], "Communes avec ventes", f"{len(medians)} / {len(contours['features'])}", f"{prices['year']}, {property_type.lower()}")
ui.tile(row[1], "Ventes retenues", ui.number(sales), "un seul logement par mutation, hors valeurs aberrantes")
ui.tile(row[2], "Médiane des communes", ui.euro(pd.Series(medians).median()) + "/m²" if medians else "n.d.", "médiane des prix médians communaux")
busiest = max(prices["communes"], key=lambda c: c["salesCount"], default=None)
ui.tile(
    row[3], "Commune la plus active",
    ui.euro(busiest["medianPriceM2"]) + "/m²" if busiest and busiest["medianPriceM2"] is not None else "n.d.",
    f"{busiest['name'] or busiest['inseeCode']}, {ui.number(busiest['salesCount'])} ventes" if busiest else None,
)

# ----------------------------------------------------------------- Carte en classes
MIN_SALES = st.slider(
    "Nombre minimal de ventes pour colorer une commune", 1, 20, 3,
    help="Sous ce seuil, le prix médian repose sur trop peu de ventes pour être représentatif : la commune reste en gris.",
)
reliable = [c["medianPriceM2"] for c in prices["communes"] if c["medianPriceM2"] is not None and c["salesCount"] >= MIN_SALES]
bounds = charts.classes(reliable)

lons, lats = [], []
for feature in contours["features"]:
    code = feature["properties"]["code"]
    data = by_commune.get(code)
    shown = data if data and data["salesCount"] >= MIN_SALES else None
    feature["properties"]["fill"] = charts.hex_to_rgb(charts.class_color(shown["medianPriceM2"] if shown else None, bounds)) + [215]
    feature["properties"]["priceLabel"] = ui.euro(data["medianPriceM2"]) + "/m²" if data and data["medianPriceM2"] is not None else "aucune vente"
    feature["properties"]["salesLabel"] = ui.number(data["salesCount"]) if data else "0"
    ring = feature["geometry"]["coordinates"][0] if feature["geometry"]["type"] == "Polygon" else feature["geometry"]["coordinates"][0][0]
    lons += [p[0] for p in ring]
    lats += [p[1] for p in ring]

layer = pdk.Layer(
    "GeoJsonLayer",
    contours,
    pickable=True,
    stroked=True,
    filled=True,
    get_fill_color="properties.fill",
    get_line_color=[252, 252, 251],
    line_width_min_pixels=0.6,
    auto_highlight=True,
)
view = pdk.ViewState(longitude=(min(lons) + max(lons)) / 2, latitude=(min(lats) + max(lats)) / 2, zoom=8, min_zoom=6)
st.pydeck_chart(
    pdk.Deck(
        layers=[layer],
        initial_view_state=view,
        map_style="light",
        tooltip={"html": "<b>{name}</b> ({code})<br/>Prix médian : {priceLabel}<br/>Ventes : {salesLabel}"},
    ),
    height=560,
)
charts.class_legend(bounds, lambda v: ui.euro(v) + "/m²", f"moins de {MIN_SALES} vente(s)")
st.caption(
    f"Prix médian au m² des ventes de {prices['year']} ({property_type.lower()}), classes d’effectifs égaux. "
    "Source : DVF géolocalisé (DGFiP), contours API Géo."
)

# ----------------------------------------------------------------- Classement
st.subheader("Communes du département")
df = pd.DataFrame(prices["communes"])
df = df.sort_values("salesCount", ascending=False)
selection = st.dataframe(
    df[["inseeCode", "name", "salesCount", "medianPriceM2", "q1PriceM2", "q3PriceM2", "meanPriceM2"]],
    hide_index=True,
    width="stretch",
    height=380,
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        "inseeCode": "INSEE",
        "name": "Commune",
        "salesCount": st.column_config.NumberColumn("Ventes", format="localized"),
        "medianPriceM2": st.column_config.NumberColumn("Médiane €/m²", format="%.0f"),
        "q1PriceM2": st.column_config.NumberColumn("1er quartile", format="%.0f"),
        "q3PriceM2": st.column_config.NumberColumn("3e quartile", format="%.0f"),
        "meanPriceM2": st.column_config.NumberColumn("Moyenne", format="%.0f"),
    },
)
picked = selection["selection"]["rows"]
if picked:
    commune = df.iloc[picked[0]]
    st.session_state["insee"] = commune["inseeCode"]
    st.page_link("views/commune.py", label=f"Ouvrir la fiche de {commune['name']}", icon=":material/location_city:")
else:
    st.caption("Sélectionner une ligne pour ouvrir la fiche de la commune.")

with st.expander("Mettre à jour les données du département"):
    st.write("Importe une autre année de ventes DVF (les indices de prix des communes sont recalculés).")
    import_year = st.number_input("Année à importer", 2019, 2100, value=(years[-1] if years else 2024))
    if st.button("Importer cette année"):
        result = ui.run(f"Import DVF {import_year}", lambda: api.post(f"/departments/{dep}/dvf/collect", years=str(import_year)))
        if result:
            ui.outcomes_table(result)
