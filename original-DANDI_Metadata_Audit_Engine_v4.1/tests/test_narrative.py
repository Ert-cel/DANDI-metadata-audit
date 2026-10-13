from metadata_audit.extractors.narrative import extract_narrative_evidence


def test_wavelength_context_is_separated():
    text = "Excitation was delivered at 470 nm. Emission was collected through a 525 nm bandpass filter."
    evidence = extract_narrative_evidence(text, "Confirmed publication methods (PMC)", "PMC:test — Imaging")
    by_field = {item.audit_field: item.value for item in evidence}
    assert by_field["excitation_wavelength"] == "470 nm"
    assert by_field["emission_wavelength"] == "525 nm"


def test_blackrock_is_acquisition_equipment():
    text = "Signals were acquired with a Blackrock Microsystems recording system."
    evidence = extract_narrative_evidence(text, "Confirmed publication methods (PMC)", "PMC:test — Electrophysiology")
    assert any(item.audit_field == "acquisition_equipment" for item in evidence)
    assert all(item.supporting_text for item in evidence)


def test_plexon_offline_sorter_is_analysis_software_not_equipment():
    text = "Spikes were manually sorted using Plexon Offline Sorter."
    evidence = extract_narrative_evidence(text, "DANDI description", "DANDI:001177")
    assert any(item.audit_field == "analysis_software" for item in evidence)
    assert not any(item.audit_field == "acquisition_equipment" for item in evidence)


def test_clampex_is_acquisition_software():
    text = "Recordings were acquired using Clampex 10.7.0.3."
    evidence = extract_narrative_evidence(text, "Confirmed publication methods (PMC)", "PMC:test — Patch clamp")
    assert any(item.audit_field == "acquisition_software" and "Clampex" in str(item.value) for item in evidence)
    assert not any(item.audit_field == "probe_model" for item in evidence)


def test_terminal_anaesthetic_is_not_surgical_anaesthetic():
    text = "After recordings, animals were deeply anesthetized with ketamine-xylazine and transcardially perfused."
    evidence = extract_narrative_evidence(text, "Confirmed publication methods (PMC)", "PMC:test — Histology")
    assert any(item.audit_field == "terminal_anaesthesia" for item in evidence)
    assert not any(item.audit_field == "anaesthetic_type" for item in evidence)
