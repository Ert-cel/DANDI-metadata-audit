from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

import pandas as pd

from ..config import NOT_REPORTED
from ..models import Evidence
from ..utils import consensus, normalize_field_name, unique_nonempty

SOFTWARE_TERMS = re.compile(
    r"\b(software|version|clampex|pclamp|clampfit|spike2|labview|patchmaster|winwcp|open ephys gui|blackrock central)\b",
    flags=re.IGNORECASE,
)
PROBE_TERMS = re.compile(
    r"\b(neuropixels|probe|electrode|array|tetrode|optrode|silicon)\b",
    flags=re.IGNORECASE,
)
EQUIPMENT_TERMS = re.compile(
    r"\b(amplifier|digitizer|headstage|recording system|acquisition system|multiclamp|axopatch|axoclamp|blackrock|intan|cerebus|omniplex)\b",
    flags=re.IGNORECASE,
)


def _split_semicolon(values: list[Any]) -> list[str]:
    out: list[str] = []
    for value in values:
        if value is None:
            continue
        for piece in str(value).split(";"):
            piece = piece.strip()
            if piece:
                out.append(piece)
    return unique_nonempty(out)


def _device_feature_values(df: pd.DataFrame) -> dict[str, list[str]]:
    names = _split_semicolon(df["device_names"].tolist()) if "device_names" in df.columns else []
    descriptions = _split_semicolon(df["device_descriptions"].tolist()) if "device_descriptions" in df.columns else []
    models = _split_semicolon(df["device_models"].tolist()) if "device_models" in df.columns else []
    manufacturers = _split_semicolon(df["device_manufacturers"].tolist()) if "device_manufacturers" in df.columns else []

    combined = unique_nonempty(names + descriptions + models)
    software = [v for v in combined if SOFTWARE_TERMS.search(v)]
    probe_models = [v for v in unique_nonempty(models + descriptions) if PROBE_TERMS.search(v) and not SOFTWARE_TERMS.search(v)]
    probes = [v for v in combined if PROBE_TERMS.search(v) and not SOFTWARE_TERMS.search(v)]
    equipment = [v for v in combined if EQUIPMENT_TERMS.search(v) and not SOFTWARE_TERMS.search(v)]

    return {
        "software": software,
        "probe_models": probe_models,
        "probes": probes,
        "equipment": equipment,
        "manufacturers": manufacturers,
    }


def structured_evidence(
    dandiset_id: str,
    dandiset_metadata: dict[str, Any],
    nwb_rows: list[dict[str, Any]],
    modality: dict[str, Any],
) -> list[Evidence]:
    df = pd.DataFrame(nwb_rows)

    def values(column: str) -> list[Any]:
        if column not in df.columns:
            return []
        if "extraction_status" in df.columns:
            return df.loc[df["extraction_status"] == "Success", column].tolist()
        return df[column].tolist()

    success_df = df
    if "extraction_status" in df.columns:
        success_df = df.loc[df["extraction_status"] == "Success"]
    device_features = _device_feature_values(success_df)

    assets_summary = dandiset_metadata.get("assetsSummary", {}) or {}
    species_summary = [i.get("name") for i in assets_summary.get("species", []) if isinstance(i, dict)]

    definitions = {
        "subject_id": (values("subject_id"), "/general/subject/subject_id", "High"),
        "sex": (values("sex"), "/general/subject/sex", "High"),
        "date_of_birth": (values("date_of_birth"), "/general/subject/date_of_birth", "High"),
        "strain": (values("strain"), "/general/subject/strain", "High"),
        "species": (values("species") + species_summary, "/general/subject/species; assetsSummary.species", "High"),
        "genotype": (values("genotype"), "/general/subject/genotype", "High"),
        "start_date": (values("session_start_time"), "/session_start_time", "High"),
        "acquisition_start_time": (values("session_start_time"), "/session_start_time", "High"),
        "instrument_id": (values("device_names"), "/general/devices", "Medium"),
        # Probe model is intentionally restricted to probe/electrode-like device metadata.
        # Generic device descriptions such as "Software: Clampex 10.7" no longer map here.
        "probe_model": (device_features["probe_models"], "/general/devices (probe/electrode filtered)", "Medium"),
        "electrode_or_probe": (device_features["probes"], "/general/devices (probe/electrode filtered)", "Medium"),
        "acquisition_equipment": (device_features["equipment"], "/general/devices (equipment filtered)", "Medium"),
        "acquisition_software": (device_features["software"], "/general/devices (software filtered)", "Medium"),
        "equipment_manufacturer": (device_features["manufacturers"], "/general/devices/*/manufacturer", "Medium"),
        "primary_targeted_structure": (values("electrode_locations"), "/general/extracellular_ephys/*/location", "Medium"),
        "modalities": (modality.get("detected_modalities", []), "DANDI assetsSummary + NWB object types", "High"),
        "stimulus_name": (values("stimulus_object_names"), "/stimulus", "Medium"),
        "channels": (values("acquisition_object_names"), "/acquisition", "Low"),
        "Ephys Probe: name": (values("electrode_group_devices"), "/general/extracellular_ephys/*/device", "Medium"),
    }

    out: list[Evidence] = []
    for field, (field_values, path, confidence) in definitions.items():
        value = consensus(field_values)
        if value == NOT_REPORTED:
            continue
        out.append(Evidence(
            audit_field=field,
            value=value,
            source_type="Structured NWB/DANDI API",
            source_location=path,
            confidence=confidence,
            review_status="Structured Evidence" if confidence == "High" else "Needs Review",
        ))
    return out


def field_key(value: str) -> str:
    return normalize_field_name(value)


def choose_best_evidence(headers: list[str], evidence: list[Evidence]) -> dict[str, Evidence]:
    by_field: dict[str, list[Evidence]] = defaultdict(list)
    for item in evidence:
        by_field[field_key(item.audit_field)].append(item)

    confidence_rank = {"High": 3, "Medium": 2, "Low": 1, "—": 0}
    source_rank = {
        "Structured NWB/DANDI API": 5,
        "CatalystNeuro curated dataset metadata": 4,
        "Confirmed publication methods (PMC)": 3,
        "Confirmed CatalystNeuro page": 2,
        "DANDI description": 1,
    }

    selected: dict[str, Evidence] = {}
    for header in headers:
        candidates = by_field.get(field_key(header), [])
        if not candidates:
            selected[header] = Evidence(
                audit_field=header,
                value=NOT_REPORTED,
                source_type="Not found in checked sources",
                confidence="—",
                review_status="Missing",
                notes="Not found in DANDI, structured NWB, confirmed CatalystNeuro sources, or associated publication methods.",
            )
            continue
        candidates.sort(
            key=lambda x: (confidence_rank.get(x.confidence, 0), source_rank.get(x.source_type, 0)),
            reverse=True,
        )
        selected[header] = candidates[0]
    return selected
