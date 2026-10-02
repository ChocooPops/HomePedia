from app.modules.services.service import opens_on_sunday


def test_detecte_les_horaires_osm_ouverts_le_dimanche():
    assert opens_on_sunday("Mo-Sa 07:00-19:30; Su 07:00-12:30") is True
    assert opens_on_sunday("Mo-Sa 07:00-19:00; Su off") is False
    assert opens_on_sunday("Tu-Sa 07:00-19:00") is False
    assert opens_on_sunday(None) is None
