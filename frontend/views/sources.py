import pandas as pd
import streamlit as st

from lib import api, ui

st.title("Sources et collectes")
st.caption("Registre des sources interrogées et journal des collectes (traçabilité, erreurs, durées).")

STATUSES = {"verified": "✓ Vérifiée", "degraded": "▲ Dégradée", "untested": "○ Non testée", "obsolete": "✕ Obsolète"}

registry, logs = st.tabs(["Registre des sources", "Journal des collectes"])

with registry:
    try:
        sources = api.get("/sources")
    except api.ApiError as err:
        st.error(err.message)
        st.stop()
    df = pd.DataFrame(sources)
    df["Validité"] = (df["ttlSeconds"] / 86400).round().astype(int).astype(str) + " j"
    df["État"] = df["status"].map(STATUSES)
    df["Clé API"] = df["requiresKey"].map({True: "Requise", False: "Non"})
    domains = ["Tous", *sorted(df["domain"].unique())]
    domain = st.selectbox("Domaine", domains)
    if domain != "Tous":
        df = df[df["domain"] == domain]
    st.dataframe(
        df[["domain", "name", "code", "État", "Clé API", "Validité", "baseUrl", "notes"]].rename(
            columns={"domain": "Domaine", "name": "Source", "code": "Code", "baseUrl": "Adresse", "notes": "Remarques"}
        ),
        hide_index=True, width="stretch", height=560,
    )
    st.caption(f"{len(df)} source(s). La validité est la durée pendant laquelle une collecte réussie n’est pas rejouée.")

with logs:
    row = st.columns([1.5, 1, 1.5])
    source = row[0].text_input("Code de la source", placeholder="georisques") or None
    status = row[1].selectbox("Résultat", [None, "success", "error", "skipped"], format_func=lambda s: ui.STATUS_LABELS.get(s, "Tous"))
    target = row[2].text_input("Cible commence par", placeholder="address:1 ou commune:80021") or None
    try:
        result = api.get("/sources/fetch-logs", source=source, status=status, target=target, limit=200)
    except api.ApiError as err:
        st.error(err.message)
        st.stop()
    rows = [
        {**r, "status": ui.STATUS_LABELS.get(r["status"], r["status"]), "fetchedAt": r["fetchedAt"][:19].replace("T", " ")}
        for r in result["items"]
    ]
    ui.table(rows, {
        "fetchedAt": "Date (UTC)", "sourceCode": "Source", "targetKey": "Cible", "status": "Résultat", "itemsCount": "Éléments",
        "durationMs": "Durée ms", "httpStatus": "HTTP", "errorMessage": "Erreur",
    }, height=560)
    st.caption(f"{ui.number(result['total'])} collecte(s) au total, les {len(rows)} plus récentes affichées.")
