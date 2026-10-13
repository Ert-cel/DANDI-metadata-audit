from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any


PRIMARY_RECORDING_MODALITIES = (
    "Fiber photometry",
    "Calcium imaging",
    "Intracellular electrophysiology",
    "Extracellular electrophysiology",
    "Electrophysiology",
)

SUPPORTING_MODALITIES = (
    "Behavioral data",
    "Optogenetic stimulation",
)


STRUCTURED_PATTERNS: dict[str, tuple[str, ...]] = {
    "Fiber photometry": (
        "fiber photometry",
        "fiber-photometry",
        "fiberphotometry",
        "photometry",
    ),
    "Calcium imaging": (
        "calcium imaging",
        "optical physiology",
        "ophys",
        "two-photon",
        "two photon",
        "2-photon",
        "one-photon",
        "one photon",
        "miniscope",
        "fluorescence imaging",
        "functional imaging",
    ),
    "Intracellular electrophysiology": (
        "intracellular electrophysiology",
        "patch clamp",
        "patch-clamp",
        "whole-cell",
        "whole cell",
        "current clamp",
        "voltage clamp",
    ),
    "Extracellular electrophysiology": (
        "extracellular electrophysiology",
        "extracellular recording",
        "electrode recording",
        "neuropixels",
        "spike sorting",
        "local field potential",
    ),
    "Electrophysiology": (
        "electrophysiology",
        "ephys",
    ),
    "Behavioral data": (
        "behavior",
        "behaviour",
        "behavioral",
        "behavioural",
        "locomotion",
        "tracking",
    ),
    "Optogenetic stimulation": (
        "optogenetic",
        "optogenetics",
        "optical stimulation",
    ),
}

NWB_TYPE_PATTERNS: dict[str, tuple[str, ...]] = {
    "Fiber photometry": (
        "fiberphotometryresponseseries",
        "fiberphotometry",
        "photometryresponseseries",
    ),
    "Calcium imaging": (
        "twophotonseries",
        "onephotonseries",
        "roiresponseseries",
        "imagesegmentation",
        "fluorescence",
        "imagingplane",
        "plane segmentation",
    ),
    "Intracellular electrophysiology": (
        "voltageclampseries",
        "currentclampseries",
        "currentclampstimulusseries",
        "voltageclampstimulusseries",
        "intracellularrecording",
    ),
    "Extracellular electrophysiology": (
        "electricalseries",
        "spikeeventseries",
        "lfp",
        "eventdetection",
        "units",
        "electrodegroup",
    ),
    "Behavioral data": (
        "position",
        "spatialseries",
        "behavioraltimeintervals",
        "pupiltracking",
    ),
    "Optogenetic stimulation": (
        "optogeneticseries",
        "optogeneticstimulussite",
    ),
}

# If multiple recording modalities are present, explicit DANDI structured
# metadata decides first. This priority is used only to break genuine ties.
PRIMARY_TIE_BREAK_PRIORITY = {
    "Fiber photometry": 5,
    "Calcium imaging": 4,
    "Intracellular electrophysiology": 3,
    "Extracellular electrophysiology": 2,
    "Electrophysiology": 1,
}


def _to_searchable_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.lower()
    try:
        return json.dumps(value, ensure_ascii=False, default=str).lower()
    except TypeError:
        return str(value).lower()


def _structured_summary_text(dandiset_metadata: dict[str, Any]) -> str:
    summary = dandiset_metadata.get("assetsSummary", {}) or {}
    selected = {
        "approach": summary.get("approach", []),
        "measurementTechnique": summary.get("measurementTechnique", []),
        "variableMeasured": summary.get("variableMeasured", []),
        "dataStandard": summary.get("dataStandard", []),
    }
    return _to_searchable_text(selected)


def _description_text(dandiset_metadata: dict[str, Any]) -> str:
    selected = {
        "name": dandiset_metadata.get("name"),
        "description": dandiset_metadata.get("description"),
        "keywords": dandiset_metadata.get("keywords"),
    }
    return _to_searchable_text(selected)


def _nwb_type_text(
    nwb_rows: list[dict[str, Any]],
    object_rows: list[dict[str, Any]],
) -> str:
    selected_objects = [
        {
            "object_category": row.get("object_category"),
            "object_name": row.get("object_name"),
            "neurodata_type": row.get("neurodata_type"),
            "description": row.get("description"),
        }
        for row in object_rows
    ]
    selected_files = [
        {
            "acquisition_object_names": row.get("acquisition_object_names"),
            "stimulus_object_names": row.get("stimulus_object_names"),
            "processing_module_names": row.get("processing_module_names"),
            "analysis_object_names": row.get("analysis_object_names"),
            "electrode_count": row.get("electrode_count"),
        }
        for row in nwb_rows
        if row.get("extraction_status") == "Success"
    ]
    return _to_searchable_text(
        {"objects": selected_objects, "files": selected_files}
    )


def _matched_terms(text: str, terms: tuple[str, ...]) -> list[str]:
    return [term for term in terms if term in text]


def classify_detected_modalities(
    dandiset_metadata: dict[str, Any],
    nwb_rows: list[dict[str, Any]] | None = None,
    object_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Classify a Dandiset without assuming every NWB file is ephys.

    Evidence is weighted as follows:
    1. Structured DANDI ``assetsSummary`` terms (strongest)
    2. Structured NWB neurodata types and objects
    3. Dandiset title/description/keywords (supporting evidence only)

    The result deliberately supports multiple modalities. ``primary_modality``
    is the main recording modality, while ``all_modalities`` may also include
    behavior or optogenetic stimulation.
    """
    nwb_rows = nwb_rows or []
    object_rows = object_rows or []

    structured_text = _structured_summary_text(dandiset_metadata)
    nwb_text = _nwb_type_text(nwb_rows, object_rows)
    description_text = _description_text(dandiset_metadata)

    scores: defaultdict[str, int] = defaultdict(int)
    evidence: defaultdict[str, list[str]] = defaultdict(list)

    for modality, terms in STRUCTURED_PATTERNS.items():
        matches = _matched_terms(structured_text, terms)
        if matches:
            scores[modality] += 100 + 10 * len(matches)
            evidence[modality].append(
                "DANDI assetsSummary: " + ", ".join(matches)
            )

    for modality, terms in NWB_TYPE_PATTERNS.items():
        matches = _matched_terms(nwb_text, terms)
        if matches:
            scores[modality] += 35 + 5 * len(matches)
            evidence[modality].append(
                "Structured NWB objects: " + ", ".join(matches)
            )

    # An electrode table is useful evidence, but it must not override an
    # explicit imaging or photometry classification in DANDI metadata.
    electrode_counts = [
        int(row.get("electrode_count") or 0)
        for row in nwb_rows
        if row.get("extraction_status") == "Success"
    ]
    if any(count > 0 for count in electrode_counts):
        scores["Extracellular electrophysiology"] += 20
        evidence["Extracellular electrophysiology"].append(
            "Structured NWB: one or more files contain an electrode table"
        )

    for modality, terms in STRUCTURED_PATTERNS.items():
        matches = _matched_terms(description_text, terms)
        if matches:
            scores[modality] += 5 + len(matches)
            evidence[modality].append(
                "Dandiset description/title: " + ", ".join(matches)
            )

    # Avoid reporting generic Electrophysiology in addition to a known subtype.
    if (
        scores["Intracellular electrophysiology"] > 0
        or scores["Extracellular electrophysiology"] > 0
    ):
        scores.pop("Electrophysiology", None)
        evidence.pop("Electrophysiology", None)

    detected = [name for name, score in scores.items() if score > 0]
    detected.sort(key=lambda name: (-scores[name], name))

    primary_candidates = [
        name for name in detected if name in PRIMARY_RECORDING_MODALITIES
    ]

    if primary_candidates:
        primary_modality = max(
            primary_candidates,
            key=lambda name: (
                scores[name],
                PRIMARY_TIE_BREAK_PRIORITY.get(name, 0),
            ),
        )
    elif "Behavioral data" in detected:
        primary_modality = "Behavioral data"
    else:
        primary_modality = "Other / unclassified"

    all_modalities = detected or ["Other / unclassified"]

    primary_evidence = evidence.get(primary_modality, [])
    has_structured_dandi = any(
        item.startswith("DANDI assetsSummary") for item in primary_evidence
    )
    has_structured_nwb = any(
        item.startswith("Structured NWB") for item in primary_evidence
    )
    if has_structured_dandi:
        confidence = "High"
    elif has_structured_nwb:
        confidence = "Medium"
    else:
        confidence = "Low"

    return {
        "primary_modality": primary_modality,
        "all_modalities": all_modalities,
        "confidence": confidence,
        "evidence": dict(evidence),
        "scores": dict(scores),
    }


def audit_sheet_for_modality(primary_modality: str) -> str:
    if primary_modality in {
        "Electrophysiology",
        "Extracellular electrophysiology",
        "Intracellular electrophysiology",
    }:
        return "Ephys Audit"
    if primary_modality == "Fiber photometry":
        return "Fiber Photometry Audit"
    if primary_modality == "Calcium imaging":
        return "Calcium Imaging Audit"
    return "Other Modalities Audit"


def modality_evidence_summary(classification: dict[str, Any]) -> str:
    primary = classification.get("primary_modality", "Other / unclassified")
    evidence = classification.get("evidence", {}).get(primary, [])
    return "; ".join(evidence) if evidence else "No positive modality evidence found"
