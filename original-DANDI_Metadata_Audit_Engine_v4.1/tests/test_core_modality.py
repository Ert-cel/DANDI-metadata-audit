from metadata_audit.processing.modality import combine_modality_sources, audit_sheet_for_modality


def test_catalyst_modality_drives_sheet():
    catalyst = {"Catalyst Modality": "Calcium imaging"}
    dandi = {"assetsSummary": {}}
    combined = combine_modality_sources(catalyst, dandi, [], [])
    assert combined["primary_modality"] == "Calcium imaging"
    assert audit_sheet_for_modality(combined["primary_modality"]) == "Calcium Imaging Audit"


def test_fiber_photometry_curated_route():
    catalyst = {"Catalyst Modality": "Fiber photometry"}
    combined = combine_modality_sources(catalyst, {"assetsSummary": {}}, [], [])
    assert audit_sheet_for_modality(combined["primary_modality"]) == "Fiber Photometry Audit"
