import pandas as pd
import streamlit as st

from lib import api, ui

st.title("Avis")
st.caption("Avis sur les quartiers, les agences et les lieux : imports MeilleursAgents et collecte Google Maps.")

SOURCES = {None: "Toutes", "meilleursagents": "MeilleursAgents", "google_places": "Google Maps"}
KINDS = {None: "Tous", "neighbourhood": "Quartier", "agency": "Agence", "place": "Lieu"}
# Champ de l'API -> libellé ; « subject » est le seul obligatoire.
FIELDS = {
    "subject": "Quartier ou agence (obligatoire)", "rating": "Note sur 5", "text": "Texte de l’avis", "author": "Auteur",
    "date": "Date", "city": "Commune", "postalCode": "Code postal", "inseeCode": "Code INSEE", "url": "Lien",
}
GUESSES = {
    "subject": ("quartier", "agence", "nom", "name", "subject", "lieu"), "rating": ("note", "rating", "score"),
    "text": ("avis", "texte", "commentaire", "text", "review"), "author": ("auteur", "author", "pseudo"), "date": ("date",),
    "city": ("ville", "commune", "city"), "postalCode": ("postal", "cp"), "inseeCode": ("insee",), "url": ("url", "lien", "link"),
}

browse, imports, google = st.tabs(["Consulter", "Importer un fichier MeilleursAgents", "Collecter les avis Google"])

# ----------------------------------------------------------------- Consultation
with browse:
    row = st.columns([1.2, 1, 1, 1, 2])
    insee = row[0].text_input("Commune (code INSEE)", value=st.session_state.get("insee") or "", max_chars=5) or None
    source = row[1].selectbox("Source", list(SOURCES), format_func=SOURCES.get)
    kind = row[2].selectbox("Type", list(KINDS), format_func=KINDS.get)
    min_rating = row[3].number_input("Note minimale", min_value=0.0, max_value=5.0, value=None, step=0.5)
    text = row[4].text_input("Texte recherché", placeholder="calme, commerces, bruit…")
    try:
        result = api.get("/reviews", insee=insee, source=source, kind=kind, minRating=min_rating, q=text if len(text) >= 2 else None, limit=100)
    except api.ApiError as err:
        st.error(err.message)
        result = {"total": 0, "items": []}
    st.subheader(f"{ui.number(result['total'])} avis")
    for review in result["items"]:
        with st.container(border=True):
            rating = f"{ui.number(review['rating'], 1)} / 5" if review.get("rating") is not None else "sans note"
            st.markdown(f"**{review.get('subjectName', '')}** · {rating}")
            if review.get("text"):
                st.write(review["text"])
            st.caption(" · ".join(str(x) for x in (
                review.get("author"), (review.get("publishedAt") or "")[:10], review.get("city") or review.get("inseeCode"),
                SOURCES.get(review["source"]), KINDS.get(review["kind"]),
            ) if x))
    if not result["items"]:
        st.info("Aucun avis ne correspond.")

# ----------------------------------------------------------------- Import de fichier
with imports:
    st.write(
        "MeilleursAgents n’a pas d’API publique : les avis s’importent depuis un fichier exporté à la main (CSV). "
        "Un avis déjà importé est mis à jour, jamais dupliqué."
    )
    kind = st.radio("Les avis portent sur", ["neighbourhood", "agency"], format_func=lambda k: {"neighbourhood": "des quartiers", "agency": "des agences"}[k], horizontal=True)
    upload = st.file_uploader("Fichier CSV", type=["csv"])
    if upload:
        try:
            df = pd.read_csv(upload, sep=None, engine="python", dtype=str).fillna("")
        except Exception as err:  # noqa: BLE001 - fichier illisible : on l'explique à l'utilisateur
            st.error(f"Fichier illisible : {err}")
            st.stop()
        st.dataframe(df.head(5), hide_index=True, width="stretch")
        st.caption(f"{len(df)} ligne(s), aperçu des 5 premières. Associer les colonnes du fichier aux champs :")
        options = [None, *df.columns]
        mapping = {}
        columns = st.columns(3)
        for i, (field, label) in enumerate(FIELDS.items()):
            guess = next((c for c in df.columns if any(g in c.lower() for g in GUESSES[field])), None)
            mapping[field] = columns[i % 3].selectbox(label, options, index=options.index(guess) if guess else 0, format_func=lambda c: c or "(aucune)")
        default_insee = st.text_input("Code INSEE à appliquer aux lignes qui n’en ont pas", value=st.session_state.get("insee") or "", max_chars=5)

        if st.button("Importer", type="primary", disabled=not mapping["subject"]):
            items = []
            for record in df.to_dict("records"):
                item = {field: str(record[column]).strip() for field, column in mapping.items() if column and str(record[column]).strip()}
                if "subject" not in item:
                    continue
                if "rating" in item:
                    try:
                        item["rating"] = float(item["rating"].replace(",", "."))
                    except ValueError:
                        del item["rating"]
                if default_insee and "inseeCode" not in item:
                    item["inseeCode"] = default_insee
                items.append(item)
            created = updated = 0
            failed = False
            for start in range(0, len(items), 2000):
                res = ui.run("Import des avis", lambda start=start: api.post("/reviews/import", {"kind": kind, "items": items[start : start + 2000]}))
                if res is None:
                    failed = True
                    break
                created += res["created"]
                updated += res["updated"]
            if not failed:
                st.success(f"{created} avis ajouté(s), {updated} mis à jour, {len(df) - len(items)} ligne(s) ignorée(s) faute de quartier ou d’agence.")

# ----------------------------------------------------------------- Google
with google:
    st.write(
        "Collecte les avis des lieux situés autour d’une adresse déjà analysée. L’API Google Maps Places est payante "
        "et renvoie au plus 5 avis par lieu ; la clé se renseigne dans GOOGLE_MAPS_API_KEY côté API."
    )
    addresses = api.try_get("/addresses", {"items": []}, limit=200)["items"]
    names = {a["id"]: a["label"] for a in addresses}
    if not names:
        st.info("Analyser d’abord une adresse.")
    else:
        left, right = st.columns([3, 1])
        address_id = left.selectbox("Adresse", list(names), format_func=names.get)
        radius = right.number_input("Rayon (m)", 50, 5000, 500, step=50)
        if st.button("Collecter les avis autour de cette adresse"):
            outcome = ui.run("Interrogation de Google Maps", lambda: api.post(f"/addresses/{address_id}/reviews/collect", radius=radius))
            if outcome:
                ui.outcomes_table([outcome])
