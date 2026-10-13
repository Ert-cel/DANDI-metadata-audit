from metadata_audit.processing.mapping import structured_evidence


def test_software_device_description_does_not_become_probe_model():
    rows = [{
        "extraction_status": "Success",
        "device_names": "Axon pCLAMP",
        "device_descriptions": "Software: Clampex 10.7.0.3",
        "device_models": None,
        "device_manufacturers": "Molecular Devices",
    }]
    evidence = structured_evidence("001777", {"assetsSummary": {}}, rows, {"detected_modalities": ["Intracellular electrophysiology"]})
    fields = {item.audit_field: item.value for item in evidence}
    assert "probe_model" not in fields
    assert "acquisition_software" in fields
    assert "Clampex" in str(fields["acquisition_software"])
