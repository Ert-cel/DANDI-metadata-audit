from __future__ import annotations

from typing import Any

from .modality_detect import classify_detected_modalities


CATALYST_NORMALIZATION = {
    "Extra ephys": "Extracellular electrophysiology",
    "Intra ephys": "Intracellular electrophysiology",
    "Intra ephys / line scans": "Intracellular electrophysiology / line scans",
    "Calcium imaging": "Calcium imaging",
    "Calcium imaging / intra ephys": "Calcium imaging / intracellular electrophysiology",
    "Fiber photometry": "Fiber photometry",
    "Fiber photometry / EEG": "Fiber photometry / EEG",
    "Extra ephys / FSCV": "Extracellular electrophysiology / FSCV",
    "EEG / EMG / DLC": "EEG / EMG / DLC",
}


def normalize_catalyst_modality(value: str) -> str:
    value = (value or "").strip()
    return CATALYST_NORMALIZATION.get(value, value)


def _terms(value: str) -> set[str]:
    text = value.lower()
    result: set[str] = set()
    if "fiber photometry" in text or "photometry" in text:
        result.add("Fiber photometry")
    if "calcium imaging" in text or "ophys" in text:
        result.add("Calcium imaging")
    if "intra" in text or "intracellular" in text or "patch" in text:
        result.add("Intracellular electrophysiology")
    if "extra" in text or "extracellular" in text:
        result.add("Extracellular electrophysiology")
    if "eeg" in text:
        result.add("EEG")
    if "fscv" in text:
        result.add("FSCV")
    return result


def combine_modality_sources(
    catalyst_record: dict[str, Any],
    dandiset_metadata: dict[str, Any],
    nwb_rows: list[dict[str, Any]],
    object_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    detected = classify_detected_modalities(dandiset_metadata, nwb_rows, object_rows)
    catalyst_raw = str(catalyst_record.get("Catalyst Modality", "") or "")
    catalyst = normalize_catalyst_modality(catalyst_raw)
    detected_list = detected.get("all_modalities", [])

    if catalyst:
        primary = catalyst
        expected = _terms(catalyst)
        found = set(detected_list)
        if not expected:
            agreement = "Not comparable"
        elif expected & found:
            agreement = "Match" if expected.issubset(found) else "Partial match"
        else:
            agreement = "Conflict / review"
        source = "CatalystNeuro ASAP curated metadata"
    else:
        primary = detected.get("primary_modality", "Other / unclassified")
        agreement = "No Catalyst classification"
        source = "DANDI/NWB detected"

    return {
        "primary_modality": primary,
        "catalyst_modality": catalyst_raw,
        "detected_modalities": detected_list,
        "all_modalities": detected_list,
        "agreement": agreement,
        "source": source,
        "detected_confidence": detected.get("confidence", "Low"),
        "detected_evidence": detected.get("evidence", {}),
    }


def audit_sheet_for_modality(primary: str) -> str:
    text = (primary or "").lower()
    if "fiber photometry" in text:
        return "Fiber Photometry Audit"
    if "calcium imaging" in text:
        return "Calcium Imaging Audit"
    if "ephys" in text or "electrophysiology" in text:
        return "Ephys Audit"
    return "Other Modalities Audit"
