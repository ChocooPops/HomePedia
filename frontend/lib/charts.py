"""
Graphiques Altair au style commun : une teinte par rôle, marques fines, grille discrète, infobulle au survol.
Palette catégorielle dans un ordre fixe (la couleur suit la série, jamais son rang) ; rampe bleue pour les grandeurs.
"""

import altair as alt
import pandas as pd
import streamlit as st

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
# Rampe séquentielle (clair -> foncé) pour les cartes en classes.
SEQUENTIAL = ["#b7d3f6", "#6da7ec", "#2a78d6", "#1c5cab", "#0d366b"]
NO_DATA = "#e1e0d9"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"


# Nombres à la française sur les axes et dans les infobulles.
LOCALE = alt.Locale(number=alt.NumberLocale(decimal=",", thousands=" ", grouping=[3], currency=["", " €"]))


def _style(chart: alt.Chart, height: int) -> alt.Chart:
    return (
        chart.properties(height=height)
        .configure(locale=LOCALE)
        .configure_view(stroke=None)
        .configure_axis(
            gridColor=GRID, domainColor=AXIS, tickColor=AXIS, labelColor=INK_MUTED, titleColor=INK_MUTED,
            labelFontSize=12, titleFontSize=12, titleFontWeight="normal",
        )
        .configure_legend(labelColor="#52514e", titleColor=INK_MUTED, orient="top", title=None, labelFontSize=12)
    )


def _color(df: pd.DataFrame, series: str | None, order: list[str] | None):
    if not series:
        return alt.value(SERIES[0])
    domain = order or list(dict.fromkeys(df[series]))
    return alt.Color(f"{series}:N", scale=alt.Scale(domain=domain, range=SERIES[: len(domain)]), legend=alt.Legend())


def line(
    df: pd.DataFrame, x: str, y: str, *, series: str | None = None, order: list[str] | None = None,
    x_title: str = "", y_title: str = "", y_format: str = ",.0f", height: int = 280, zero: bool = False,
):
    """Évolution dans le temps : une ligne par série, point à chaque millésime observé."""
    if df.empty:
        st.info("Aucune donnée.")
        return
    base = alt.Chart(df).encode(
        # Axe continu : l'écart entre deux recensements se lit à l'échelle (1968, 1975, 1982...).
        x=alt.X(f"{x}:Q", title=x_title, scale=alt.Scale(zero=False, nice=False, padding=16), axis=alt.Axis(format="d", grid=False, tickMinStep=1)),
        y=alt.Y(f"{y}:Q", title=y_title, scale=alt.Scale(zero=zero), axis=alt.Axis(format=y_format, tickCount=5)),
        color=_color(df, series, order),
        tooltip=[alt.Tooltip(f"{x}:Q", title=x_title or x, format="d")]
        + ([alt.Tooltip(f"{series}:N", title="Série")] if series else [])
        + [alt.Tooltip(f"{y}:Q", title=y_title or y, format=y_format)],
    )
    chart = base.mark_line(strokeWidth=2) + base.mark_point(size=64, filled=True, opacity=1)
    st.altair_chart(_style(chart, height), width="stretch")


def bars(
    df: pd.DataFrame, category: str, value: str, *, series: str | None = None, order: list[str] | None = None,
    horizontal: bool = False, stacked: bool = True, value_title: str = "", category_title: str = "",
    value_format: str = ",.0f", height: int = 280, sort=None,
):
    """Comparaison de grandeurs. Empilé par série si `series` est donné."""
    if df.empty:
        st.info("Aucune donnée.")
        return
    cat = alt.X if not horizontal else alt.Y
    val = alt.Y if not horizontal else alt.X
    radius = {"cornerRadiusTopLeft": 4, "cornerRadiusTopRight": 4} if not horizontal else {"cornerRadiusTopRight": 4, "cornerRadiusBottomRight": 4}
    if series:
        radius = {}
    encodings = {
        "x" if not horizontal else "y": cat(
            f"{category}:N", title=category_title, sort=sort, axis=alt.Axis(labelAngle=0, grid=False, labelLimit=220)
        ),
        "y" if not horizontal else "x": val(
            f"{value}:Q", title=value_title, stack="zero" if (series and stacked) else None,
            axis=alt.Axis(format=value_format, tickCount=5),
        ),
        "color": _color(df, series, order),
        "tooltip": [alt.Tooltip(f"{category}:N", title=category_title or category)]
        + ([alt.Tooltip(f"{series}:N", title="Série")] if series else [])
        + [alt.Tooltip(f"{value}:Q", title=value_title or value, format=value_format)],
    }
    if series and not stacked:
        encodings["xOffset" if not horizontal else "yOffset"] = alt.XOffset(f"{series}:N") if not horizontal else alt.YOffset(f"{series}:N")
    # Liseré de la couleur du fond : sépare les segments empilés et les barres voisines.
    chart = alt.Chart(df).mark_bar(stroke="#fcfcfb", strokeWidth=1, **radius).encode(**encodings)
    st.altair_chart(_style(chart, height), width="stretch")


def classes(values: list[float], count: int = 5) -> list[float]:
    """Bornes de classes par quantiles (cartes en classes), sans doublon."""
    clean = sorted(v for v in values if v is not None)
    if not clean:
        return []
    bounds = [clean[min(len(clean) - 1, round(i * (len(clean) - 1) / count))] for i in range(1, count)]
    return sorted(set(bounds))


def _ramp(count: int) -> list[str]:
    """`count` teintes de la rampe, du clair au foncé, réparties sur toute son étendue."""
    if count >= len(SEQUENTIAL):
        return SEQUENTIAL
    if count == 1:
        return [SEQUENTIAL[2]]
    return [SEQUENTIAL[round(i * (len(SEQUENTIAL) - 1) / (count - 1))] for i in range(count)]


def class_color(value: float | None, bounds: list[float]) -> str:
    """Couleur de la classe d'une valeur : la classe i couvre ]bounds[i-1] ; bounds[i]]."""
    if value is None:
        return NO_DATA
    return _ramp(len(bounds) + 1)[sum(value > b for b in bounds)]


def hex_to_rgb(color: str) -> list[int]:
    return [int(color[i : i + 2], 16) for i in (1, 3, 5)]


def class_legend(bounds: list[float], fmt, no_data_label: str = "Pas de vente"):
    """Légende d'une carte en classes : pastilles + intervalles, puis la classe « sans donnée »."""
    ramp = _ramp(len(bounds) + 1)
    edges = [None, *bounds, None]
    items = []
    for i, color in enumerate(ramp):
        lo, hi = edges[i], edges[i + 1]
        if lo is None and hi is None:
            label = "toutes les communes"
        elif lo is None:
            label = f"jusqu’à {fmt(hi)}"
        elif hi is None:
            label = f"plus de {fmt(lo)}"
        else:
            label = f"{fmt(lo)} à {fmt(hi)}"
        items.append((color, label))
    items.append((NO_DATA, no_data_label))
    swatches = "".join(
        f'<span style="display:inline-flex;align-items:center;margin-right:16px;white-space:nowrap">'
        f'<span style="width:14px;height:14px;border-radius:3px;background:{c};display:inline-block;margin-right:6px;'
        f'border:1px solid rgba(11,11,11,0.10)"></span>{label}</span>'
        for c, label in items
    )
    st.markdown(f'<div style="font-size:13px;color:#52514e;line-height:2">{swatches}</div>', unsafe_allow_html=True)
