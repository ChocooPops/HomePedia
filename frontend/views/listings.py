import streamlit as st

from lib import api, ui

st.title("Annonces")
st.caption("Annonces immobilières remontées par le service de scraping (SeLoger, Bien’ici, Leboncoin).")

TRANSACTIONS = {None: "Toutes", "sale": "Vente", "rent": "Location"}
PROPERTIES = {None: "Tous", "apartment": "Appartement", "house": "Maison", "land": "Terrain", "parking": "Stationnement", "other": "Autre"}
SOURCES = {None: "Tous", "seloger": "SeLoger", "bienici": "Bien’ici", "leboncoin": "Leboncoin"}
SORTS = {"recent": "Plus récentes", "price": "Prix croissant", "-price": "Prix décroissant", "priceM2": "€/m² croissant", "-priceM2": "€/m² décroissant"}

row = st.columns([1.2, 1, 1, 1, 1.2])
insee = row[0].text_input("Commune (code INSEE)", value=st.session_state.get("insee") or "", max_chars=5) or None
transaction = row[1].selectbox("Transaction", list(TRANSACTIONS), format_func=TRANSACTIONS.get)
property_type = row[2].selectbox("Bien", list(PROPERTIES), format_func=PROPERTIES.get)
source = row[3].selectbox("Site", list(SOURCES), format_func=SOURCES.get)
sort = row[4].selectbox("Tri", list(SORTS), format_func=SORTS.get)
row = st.columns(5)
min_price = row[0].number_input("Prix minimal (€)", min_value=0, value=None, step=10000)
max_price = row[1].number_input("Prix maximal (€)", min_value=0, value=None, step=10000)
min_area = row[2].number_input("Surface minimale (m²)", min_value=0, value=None, step=5)
max_area = row[3].number_input("Surface maximale (m²)", min_value=0, value=None, step=5)
min_rooms = row[4].number_input("Pièces (minimum)", min_value=0, value=None, step=1)

try:
    result = api.get(
        "/listings", insee=insee, transactionType=transaction, propertyType=property_type, source=source, sort=sort,
        minPrice=min_price, maxPrice=max_price, minArea=min_area, maxArea=max_area, minRooms=min_rooms, limit=200,
    )
except api.ApiError as err:
    st.error(err.message)
    st.stop()

if insee:
    stats = api.try_get(f"/communes/{insee}/listings/stats")
    if stats and stats["groups"]:
        st.subheader("Prix au m² des annonces de la commune")
        ui.table(
            [{**g, "transactionType": TRANSACTIONS.get(g["transactionType"]), "propertyType": PROPERTIES.get(g["propertyType"])} for g in stats["groups"]],
            {"transactionType": "Transaction", "propertyType": "Bien", "listingsCount": "Annonces", "medianPriceM2": "Médiane €/m²",
             "avgPriceM2": "Moyenne €/m²", "minPriceM2": "Minimum", "maxPriceM2": "Maximum"},
        )

st.subheader(f"{ui.number(result['total'])} annonce(s)")
if not result["items"]:
    st.info(
        "Aucune annonce ne correspond. Les annonces arrivent par l’API d’ingestion (POST /api/listings/ingest), "
        "alimentée par le service de scraping."
    )
    st.stop()

rows = [
    {
        **item,
        "transactionType": TRANSACTIONS.get(item["transactionType"]),
        "propertyType": PROPERTIES.get(item["propertyType"]),
        "source": SOURCES.get(item["source"]),
        "priceChanges": max(len(item.get("priceHistory", [])) - 1, 0),
        "lastSeenAt": item["lastSeenAt"][:10],
    }
    for item in result["items"]
]
ui.table(
    rows,
    {"title": "Annonce", "city": "Commune", "transactionType": "Transaction", "propertyType": "Bien", "priceEur": "Prix €",
     "areaM2": "Surface m²", "priceM2": "€/m²", "rooms": "Pièces", "energyClass": "DPE", "priceChanges": "Changements de prix",
     "lastSeenAt": "Vue le", "source": "Site", "url": "Lien"},
    height=520,
    config={"Lien": st.column_config.LinkColumn(display_text="Ouvrir")},
)
if result["total"] > len(rows):
    st.caption(f"Les {len(rows)} premières annonces sont affichées : affiner les filtres pour voir les autres.")
