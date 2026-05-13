from lip.enrichment.location import resolve


def test_resolve_canadian_province_abbreviation():
    r = resolve("Calgary, AB")
    assert r is not None
    assert r.region_code == "CA-AB"


def test_resolve_canadian_province_long_name():
    r = resolve("Fort McMurray, Alberta")
    assert r is not None
    assert r.region_code == "CA-AB"


def test_resolve_us_state():
    r = resolve("Houston, TX")
    assert r is not None
    assert r.region_code == "US-TX"


def test_resolve_returns_none_for_empty():
    assert resolve(None) is None
    assert resolve("") is None
