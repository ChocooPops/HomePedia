import pandas as pd
import streamlit as st

from lib import api, ui

st.title("Tableau de bord")
st.caption("Volumes disponibles pour l’analyse et état des sources de données.")

try:
    overview = api.get("/overview")
except api.ApiError as err:
    st.error(f"L’API HomePedia ne répond pas. {err.message}")
    st.stop()

tables, documents = overview["tables"], overview["documents"]
row = st.columns(5)
ui.tile(row[0], "Adresses analysées", ui.number(tables["address"]))
ui.tile(row[1], "Communes référencées", ui.number(tables["commune"]))
ui.tile(row[2], "Ventes DVF", ui.number(tables["dvf_mutation"]), "lignes de mutation stockées")
ui.tile(row[3], "Annonces", ui.number(documents["listings"]), "remontées par le scraping")
ui.tile(row[4], "Avis", ui.number(documents["reviews"]), "Google Maps et MeilleursAgents")

st.subheader("Référentiel territorial")
regions = api.try_get("/regions", [])
left, right = st.columns([3, 1], vertical_alignment="center")
if regions:
    left.write(
        f"{len(regions)} régions et {len(api.try_get('/departments', []))} départements chargés, "
        f"{ui.number(documents['contours'])} contours disponibles pour les cartes."
    )
else:
    left.warning("Le référentiel (régions, départements, contours) n’est pas encore chargé.")
if right.button("Charger le référentiel" if not regions else "Actualiser le référentiel", width="stretch"):
    result = ui.run("Chargement des régions, départements et contours", lambda: api.post("/territories/collect"))
    if result:
        ui.outcomes_table(result)

st.subheader("Collectes du jour")
today = {r["status"]: r for r in overview["collectsToday"]}
row = st.columns(3)
ui.tile(row[0], "Collectes réussies", ui.number(today.get("success", {}).get("n", 0)))
ui.tile(row[1], "Sources sans clé API", ui.number(today.get("skipped", {}).get("n", 0)), "ignorées sans bloquer les autres")
ui.tile(row[2], "Collectes en erreur", ui.number(today.get("error", {}).get("n", 0)), "détail dans « Sources et collectes »")

st.subheader("Sources par domaine")
sources = pd.DataFrame(overview["sources"])
if not sources.empty:
    pivot = sources.pivot_table(index="domain", columns="status", values="n", aggfunc="sum", fill_value=0)
    labels = {"verified": "Vérifiées", "degraded": "Dégradées", "untested": "Non testées (clé requise)", "obsolete": "Obsolètes"}
    pivot = pivot.reindex(columns=[c for c in labels if c in pivot.columns]).rename(columns=labels)
    pivot.insert(0, "Total", pivot.sum(axis=1))
    pivot.index.name = "Domaine"
    st.dataframe(pivot, width="stretch")
    st.caption(f"{int(sources['n'].sum())} sources enregistrées. Le détail et le journal des collectes sont dans « Sources et collectes ».")
