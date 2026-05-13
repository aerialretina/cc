from lip.enrichment.normalize import (
    normalize_company,
    normalize_location,
    normalize_title,
)


def test_normalize_title_strips_seniority_marker():
    assert normalize_title("Project Manager III") == "project manager"
    # "Sr."/"Jr." are seniority markers we want stripped — they should not
    # cause the dedup key to differ from "Superintendent".
    assert normalize_title("Sr. Superintendent") == "superintendent"
    assert normalize_title("Superintendent") == "superintendent"


def test_normalize_company_drops_legal_suffix():
    assert normalize_company("PCL Construction Inc.") == "pcl construction"
    assert normalize_company("Aecon Group Inc.") == "aecon"
    assert normalize_company("Fluor Corporation") == "fluor"


def test_normalize_company_handles_accents():
    assert normalize_company("AtkinsRéalis") == "atkinsrealis"


def test_normalize_location_lowercases_and_strips_punct():
    assert normalize_location("Calgary, AB") == "calgary ab"
    assert normalize_location("Fort McMurray, Alberta") == "fort mcmurray alberta"


def test_normalize_handles_none():
    assert normalize_title(None) == ""
    assert normalize_company("") == ""
