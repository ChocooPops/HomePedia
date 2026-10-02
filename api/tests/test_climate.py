from app.modules.climate.normalizers import climate_indicators, projection_indicators


def test_climate_indicators_calcule_des_moyennes_annuelles():
    daily = {
        "time": ["2023-01-01", "2023-07-01", "2024-01-01", "2024-07-01"],
        "temperature_2m_min": [-3, 21, -6, 15],
        "temperature_2m_max": [2, 32, 1, 28],
        "snowfall_sum": [2, 0, 0, 0],
        "wind_gusts_10m_max": [90, 20, 30, 40],
        "sunshine_duration": [3600, 36000, 7200, 36000],
        "precipitation_sum": [10, 0, 5, 1],
    }
    by_key = {i["indicator"]: i["valueNum"] for i in climate_indicators(daily, {})}
    assert by_key["frost_days_per_year"] == 1
    assert by_key["severe_frost_days_per_year"] == 0.5
    assert by_key["tropical_nights_per_year"] == 0.5
    assert by_key["hot_days_per_year"] == 0.5
    assert by_key["strong_wind_days_per_year"] == 0.5
    assert by_key["winter_sunshine_hours"] == 1.5
    assert by_key["precipitation_per_year"] == 8


def test_projection_indicators_ignore_un_modele_sans_donnees():
    daily = {"time": ["2050-01-01"], "temperature_2m_max_A": [None], "temperature_2m_min_A": [None], "precipitation_sum_A": [None]}
    assert projection_indicators(daily, "A") == []
