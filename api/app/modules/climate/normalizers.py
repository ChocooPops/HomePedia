"""Agrégats climatiques calculés à partir des séries journalières Open-Meteo (fonctions pures, testables)."""

from collections.abc import Callable

from ...parse import js_round


def round1(v: float) -> float:
    return js_round(v * 10) / 10


def climate_indicators(daily: dict, meta: dict) -> list[dict]:
    """
    Agrégats climatiques annuels moyens à partir des séries journalières Open-Meteo (réanalyse ERA5).
    Maille ~10 km : les phénomènes très locaux (îlot de chaleur, brouillard de vallée) sont lissés.
    """
    days: list[str] = daily["time"]
    years = len({d[:4] for d in days}) or 1

    def count(key: str, pred: Callable[[float], bool]) -> float:
        return len([v for v in daily.get(key) or [] if v is not None and pred(v)]) / years

    def total(key: str, keep: Callable[[int], bool] = lambda i: True) -> float:
        return sum(v for i, v in enumerate(daily.get(key) or []) if v is not None and keep(i)) / years

    def winter(i: int) -> bool:
        return days[i][5:7] in ("12", "01", "02")

    items = [
        ("frost_days_per_year", count("temperature_2m_min", lambda v: v < 0), "jours/an"),
        ("severe_frost_days_per_year", count("temperature_2m_min", lambda v: v <= -5), "jours/an"),
        ("tropical_nights_per_year", count("temperature_2m_min", lambda v: v >= 20), "nuits/an"),
        ("hot_days_per_year", count("temperature_2m_max", lambda v: v >= 30), "jours/an"),
        ("snowfall_per_year", total("snowfall_sum"), "cm/an"),
        ("snow_days_per_year", count("snowfall_sum", lambda v: v >= 1), "jours/an"),
        ("strong_wind_days_per_year", count("wind_gusts_10m_max", lambda v: v >= 80), "jours/an"),
        ("sunshine_hours_per_year", total("sunshine_duration") / 3600, "h/an"),
        ("winter_sunshine_hours", total("sunshine_duration", winter) / 3600, "h/hiver"),
        ("precipitation_per_year", total("precipitation_sum"), "mm/an"),
    ]
    return [{"indicator": indicator, "valueNum": round1(value), "unit": unit, "details": meta} for indicator, value, unit in items]


def projection_indicators(daily: dict, model: str) -> list[dict]:
    """Indicateurs par modèle sur une période (moyennes annuelles)."""
    days: list[str] = daily["time"]
    tmax = daily.get(f"temperature_2m_max_{model}") or []
    tmin = daily.get(f"temperature_2m_min_{model}") or []
    prcp = daily.get(f"precipitation_sum_{model}") or []
    valid_years = len({d[:4] for i, d in enumerate(days) if i < len(tmax) and tmax[i] is not None})
    if valid_years == 0:
        return []

    def per(arr: list, pred: Callable[[float], bool]) -> float:
        return len([v for v in arr if v is not None and pred(v)]) / valid_years

    def mean(arr: list) -> float:
        vals = [v for v in arr if v is not None]
        return sum(vals) / (len(vals) or 1)

    return [
        {"indicator": "mean_tmax", "value": round1(mean(tmax)), "unit": "°C"},
        {"indicator": "hot_days_per_year", "value": round1(per(tmax, lambda v: v >= 30)), "unit": "jours/an"},
        {"indicator": "tropical_nights_per_year", "value": round1(per(tmin, lambda v: v >= 20)), "unit": "nuits/an"},
        {"indicator": "frost_days_per_year", "value": round1(per(tmin, lambda v: v < 0)), "unit": "jours/an"},
        {
            "indicator": "precipitation_per_year",
            "value": round1(sum(v for v in prcp if v is not None) / valid_years),
            "unit": "mm/an",
        },
    ]
