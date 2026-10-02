from datetime import datetime

from app.modules.socio.normalizers import housing_indicators

stamp = {"sourceCode": "test", "fetchedAt": datetime.now(), "expiresAt": datetime.now()}


def test_calcule_les_parts_de_residences_secondaires_et_de_logements_vacants():
    def obs(ocs: str, v: float) -> dict:
        return {"dimensions": {"TIME_PERIOD": "2023", "OCS": ocs}, "measures": {"OBS_VALUE_NIVEAU": {"value": v}}}

    rows = housing_indicators([obs("_T", 1000), obs("DW_SEC_DW_OCC", 50), obs("DW_VAC", 100)], [], "80021", stamp)
    by_key = {r["indicator"]: r["value"] for r in rows}
    assert by_key["share_secondary_homes"] == 5
    assert by_key["share_vacant_dwellings"] == 10
