from lip.enrichment.compensation import extract


def test_extract_annual_range_with_k_suffix():
    c = extract("Compensation: $120k-$150k per year, depending on experience")
    assert c is not None
    assert c.amount_low == 120_000
    assert c.amount_high == 150_000
    assert c.period == "annual"
    assert c.currency == "USD"


def test_extract_hourly_range():
    c = extract("Wage: $45 to $60 per hour")
    assert c is not None
    assert c.amount_low == 45
    assert c.amount_high == 60
    assert c.period == "hourly"


def test_extract_cad_currency():
    c = extract("Salary range: CAD 95,000-115,000 annually")
    assert c is not None
    assert c.currency == "CAD"
    assert c.amount_low == 95_000
    assert c.amount_high == 115_000


def test_extract_returns_none_when_no_match():
    assert extract("Send your CV to careers@example.com") is None
    assert extract(None) is None
