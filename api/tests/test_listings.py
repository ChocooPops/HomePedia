from app.modules.listings.normalizers import dedupe_by_source_id, department_of, normalize_listing, price_m2
from app.modules.listings.schemas import IngestListing


def item(**over) -> IngestListing:
    return IngestListing(**{
        "sourceId": " 42 ",
        "url": "https://www.bienici.com/annonce/42",
        "transactionType": "sale",
        "propertyType": "apartment",
        "priceEur": 189000,
        **over,
    })


def test_calcule_prix_au_m2_departement_et_point_geojson():
    doc = normalize_listing(
        "bienici", item(areaM2=64, inseeCode="80021", lat=49.89, lon=2.29, energyClass="d", title="  T3   lumineux ")
    )
    assert doc["sourceId"] == "42"
    assert doc["priceEur"] == 189000
    assert doc["priceM2"] == 2953
    assert doc["departmentCode"] == "80"
    assert doc["location"] == {"type": "Point", "coordinates": [2.29, 49.89]}
    assert doc["energyClass"] == "D"
    assert doc["title"] == "T3 lumineux"


def test_omet_les_cles_absentes():
    doc = normalize_listing("seloger", item(lat=49.89))
    assert "location" not in doc
    assert "priceM2" not in doc
    assert "photos" not in doc
    assert None not in doc.values()


def test_dedoublonne_les_photos():
    doc = normalize_listing("leboncoin", item(photos=["https://img.test/a.jpg", "https://img.test/a.jpg", "https://img.test/b.jpg"]))
    assert doc["photos"] == ["https://img.test/a.jpg", "https://img.test/b.jpg"]


def test_prix_au_m2():
    assert price_m2(200000, 64, False) == 3125
    assert price_m2(700, 33, True) == 21.21
    assert price_m2(200000, None, False) is None
    assert price_m2(200000, 0, False) is None
    assert price_m2(0, 50, False) is None


def test_departement():
    assert department_of("80021") == "80"
    assert department_of("2A004") == "2A"
    assert department_of("97411") == "974"
    assert department_of(None, "69003") == "69"
    assert department_of(None, "20000") is None
    assert department_of() is None


def test_garde_la_derniere_occurrence():
    out = dedupe_by_source_id([{"sourceId": "a", "v": 1}, {"sourceId": "b", "v": 2}, {"sourceId": "a", "v": 3}])
    assert out == [{"sourceId": "a", "v": 3}, {"sourceId": "b", "v": 2}]
