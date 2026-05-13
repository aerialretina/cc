from types import SimpleNamespace

from lip.enrichment.dedup import compute_dedup_key


def _raw(title, company, location):
    return SimpleNamespace(
        raw_title=title, company_raw=company, location_raw=location
    )


def test_same_role_different_title_seniority_collapses():
    a = compute_dedup_key(_raw("Senior Project Manager", "PCL Construction Inc.", "Calgary, AB"))
    b = compute_dedup_key(_raw("Senior Project Manager", "PCL Construction", "Calgary, AB"))
    assert a.hash() == b.hash()


def test_different_company_distinct_key():
    a = compute_dedup_key(_raw("Estimator", "PCL Construction Inc.", "Calgary, AB"))
    b = compute_dedup_key(_raw("Estimator", "EllisDon Corporation", "Calgary, AB"))
    assert a.hash() != b.hash()


def test_different_location_distinct_key():
    a = compute_dedup_key(_raw("Estimator", "PCL Construction Inc.", "Calgary, AB"))
    b = compute_dedup_key(_raw("Estimator", "PCL Construction Inc.", "Edmonton, AB"))
    assert a.hash() != b.hash()
