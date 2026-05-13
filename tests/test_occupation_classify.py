from lip.enrichment.occupation import classify


def test_classify_construction_superintendent():
    label = classify("Senior Construction Superintendent", description=None)
    assert label.industrial_overlay_code == "con.superintendent"
    assert label.seniority == "senior"


def test_classify_red_seal_pipefitter():
    label = classify("Journeyperson Pipefitter (Red Seal)", description="Industrial pipefitter")
    assert label.industrial_overlay_code == "tr.pipefitter"
    assert label.seniority == "journeyperson"


def test_classify_unknown_role_low_confidence():
    label = classify("Marketing Coordinator", description="Brand and content")
    assert label.industrial_overlay_code is None
    assert label.confidence < 0.5
