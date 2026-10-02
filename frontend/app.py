"""HomePedia : interface d'analyse du logement et des territoires, à l'usage des professionnels."""

import streamlit as st

st.set_page_config(page_title="HomePedia", page_icon="🏠", layout="wide")

pages = st.navigation({
    "Pilotage": [
        st.Page("views/dashboard.py", title="Tableau de bord", icon=":material/dashboard:", default=True),
    ],
    "Analyse": [
        st.Page("views/territory.py", title="Territoires", icon=":material/map:"),
        st.Page("views/commune.py", title="Fiche commune", icon=":material/location_city:"),
        st.Page("views/address.py", title="Analyse d’adresse", icon=":material/home_pin:"),
    ],
    "Marché": [
        st.Page("views/listings.py", title="Annonces", icon=":material/real_estate_agent:"),
        st.Page("views/reviews.py", title="Avis", icon=":material/reviews:"),
    ],
    "Données": [
        st.Page("views/sources.py", title="Sources et collectes", icon=":material/database:"),
    ],
})
pages.run()
