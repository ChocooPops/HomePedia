from datetime import datetime

from app.parse import bool_from_flag, int_, iso_date, js_round, normalize_label, num, parse_datetime, quantile, str_


def test_num_tolere_les_formats_francais():
    assert num("1 234,5") == 1234.5
    assert num("12 m²") == 12
    assert num("abc") is None
    assert num("") is None
    assert num(None) is None
    assert num(3) == 3


def test_int_arrondit_au_demi_superieur():
    assert int_("2,5") == 3
    assert js_round(0.5) == 1
    assert js_round(-0.5) == 0


def test_str_coupe_et_ecarte_les_valeurs_vides():
    assert str_("  abc  ", 2) == "ab"
    assert str_("Non connu") is None
    assert str_("") is None
    assert str_(12) == "12"


def test_iso_date():
    assert iso_date("01/09/2000") == "2000-09-01"
    assert iso_date("2000-09-01T10:00:00Z") == "2000-09-01"
    assert iso_date("septembre") is None


def test_parse_datetime_ramene_en_utc_sans_fuseau():
    assert parse_datetime("2026-09-28T10:12:00+02:00") == datetime(2026, 9, 28, 8, 12)
    assert parse_datetime("2026-09-28T08:12:00Z") == datetime(2026, 9, 28, 8, 12)
    assert parse_datetime("pas une date") is None


def test_bool_from_flag():
    assert bool_from_flag("Oui") is True
    assert bool_from_flag("N") is False
    assert bool_from_flag("peut-être") is None


def test_normalize_label():
    assert normalize_label("2, rue de la République") == "2 RUE DE LA REPUBLIQUE"


def test_quantile():
    assert quantile([1, 2, 3, 4], 0.5) == 2.5
    assert quantile([], 0.5) is None
