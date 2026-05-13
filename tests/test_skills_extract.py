from lip.enrichment.skills import extract


def test_extract_certifications():
    text = "Must hold Red Seal and OSHA 30. PMP an asset."
    r = extract(text)
    assert "Red Seal" in r.certifications
    assert "OSHA 30" in r.certifications
    assert "PMP" in r.certifications


def test_extract_software_skills():
    text = "Proficient in Primavera P6 and AutoCAD. Bluebeam experience required."
    r = extract(text)
    assert "Primavera P6" in r.skills
    assert "AutoCAD" in r.skills
    assert "Bluebeam Revu" in r.skills


def test_extract_handles_empty():
    r = extract(None)
    assert r.skills == []
    assert r.certifications == []
