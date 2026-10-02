from datetime import datetime

from app.modules.risk.normalizers import normalize_report

STAMP = {"sourceCode": "test", "fetchedAt": datetime(2026, 1, 1), "expiresAt": datetime(2026, 2, 1)}


def test_aplatit_le_rapport_georisques_en_une_ligne_par_alea():
    rows = normalize_report(
        {
            "risquesNaturels": {"radon": {"present": True, "libelle": "Radon", "libelleStatutAdresse": "Risque Existant - faible"}},
            "risquesTechnologiques": {"icpe": {"present": False, "libelle": "ICPE"}},
        },
        7,
        STAMP,
    )
    assert len(rows) == 2
    assert rows[0] | {"addressId": 7, "hazardCode": "radon", "category": "natural", "present": True} == rows[0]
    assert rows[1] | {"hazardCode": "icpe", "category": "technological", "present": False} == rows[1]
