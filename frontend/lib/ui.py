"""Mise en forme commune : nombres à la française, libellés, tuiles, résultats de collecte."""

import pandas as pd
import streamlit as st

from . import api

NBSP = " "

STATUS_LABELS = {
    "success": "✓ Collecté",
    "cached": "● En cache",
    "skipped": "○ Clé absente",
    "error": "✕ Erreur",
}

SECTORS = {
    "RESIDENTIEL": "Résidentiel",
    "TERTIAIRE": "Tertiaire",
    "INDUSTRIE": "Industrie",
    "AGRICULTURE": "Agriculture",
    "INCONNU": "Non affecté",
}
ENERGIES = {"electricity": "Électricité", "gas": "Gaz"}


def number(v, digits: int = 0, unit: str = "") -> str:
    """1234567.8 -> « 1 234 568 » ; None -> « n.d. »."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "n.d."
    text = f"{v:,.{digits}f}".replace(",", NBSP).replace(".", ",")
    return f"{text}{NBSP}{unit}" if unit else text


def euro(v, digits: int = 0) -> str:
    return number(v, digits, "€")


def pct(v, digits: int = 1) -> str:
    return number(v, digits, "%")


def latest(indicators: dict, key: str) -> tuple:
    """(valeur, année) du dernier millésime d'un indicateur socio-démographique."""
    item = (indicators or {}).get(key)
    return (item["value"], item["year"]) if item else (None, None)


def tile(column, label: str, value: str, caption: str | None = None, help: str | None = None):
    """Tuile chiffre clé : libellé, valeur, précision (millésime, périmètre)."""
    with column:
        st.metric(label, value, help=help, border=True)
        if caption:
            st.caption(caption)


def outcomes_table(outcomes: list[dict]):
    """Tableau des résultats d'une collecte, une ligne par source."""
    if not outcomes:
        return
    df = pd.DataFrame([
        {
            "Source": o.get("source"),
            "Cible": o.get("target"),
            "Résultat": STATUS_LABELS.get(o.get("status"), o.get("status")),
            "Éléments": o.get("items"),
            "Détail": o.get("error") or "",
        }
        for o in outcomes
    ])
    st.dataframe(df, hide_index=True, width="stretch")


def collect_summary(summary: dict) -> str:
    parts = [
        f"{summary.get('success', 0)} source(s) collectée(s)",
        f"{summary.get('cached', 0)} en cache",
        f"{summary.get('skipped', 0)} sans clé API",
        f"{summary.get('error', 0)} en erreur",
    ]
    return ", ".join(parts)


def run(label: str, action):
    """Exécute une collecte avec indicateur d'attente ; affiche l'erreur de l'API le cas échéant."""
    try:
        with st.spinner(label):
            return action()
    except api.ApiError as err:
        st.error(f"{label} : échec. {err.message}")
        return None


def table(rows: list[dict], columns: dict[str, str], *, height: int | None = None, config: dict | None = None):
    """Tableau à partir de lignes de l'API : `columns` associe clé JSON -> en-tête affiché."""
    if not rows:
        st.info("Aucune donnée.")
        return
    df = pd.DataFrame(rows)
    for key in columns:
        if key not in df.columns:
            df[key] = None
    df = df[list(columns)].rename(columns=columns)
    kwargs = {"height": height} if height else {}
    st.dataframe(df, hide_index=True, width="stretch", column_config=config or {}, **kwargs)


def not_covered(items: list[str] | None):
    if items:
        st.caption("Non couvert par les sources ouvertes : " + " ; ".join(items) + ".")
