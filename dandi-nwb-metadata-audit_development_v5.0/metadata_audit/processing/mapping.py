from __future__ import annotations

from collections import defaultdict
from typing import Any


from ..config import NOT_REPORTED
from ..models import Evidence
from ..utils import normalize_field_name


# Conservative aliases: expanding this registry requires a documented semantic
# match, not merely a shared word in a file name or description.
NWB_FIELD_ALIASES = {
    "acquisition_type": {"session_description"},
    "laser_wavelength": {"excitation_lambda", "excitation_wavelength"},
    "emission_wavelength": {"emission_lambda"},
}

CONTEXTUAL_FIELDS = {"name", "source", "size", "start_date", "position", "channels",
                     "profile", "volume", "location", "code", "unit", "type"}
PLACEHOLDER_VALUES = {"unknown", "no description", "no comments", "not reported", "n/a", "none"}


def modality_observed(modality: str, context: str, detected: set[str]) -> bool:
    """Match only methods observed in the scanned NWB assets, not the Dandiset title."""
    names = " ".join(detected).lower()
    if modality == "Electrophysiology":
        return "electrophysiology" in names
    if modality in {"Fiber photometry", "Calcium imaging"}:
        return modality.lower() in names
    if modality == "Cross-modality":
        return ("optogenetic" in names if context == "Optogenetics" else "behavior" in names)
    if modality == "Shared" and context == "Fiber photometry":
        return "fiber photometry" in names
    return True


def matches_context(field: str, source_location: str, context: str) -> bool:
    """Require the right NWB object when the same name occurs across modalities."""
    path = source_location.split(":", 1)[-1].lower()
    if field in {"subject_id", "sex", "species", "genotype", "date_of_birth", "strain"}:
        return path.startswith(("subject/", "/general/subject/"))
    if field == "channel_name" and context == "Optical channel":
        return any(term in path for term in ("optical", "photometry", "imaging"))
    if field == "channel_name":
        return False  # An extracellular electrode channel is not an optical channel.
    return True


def nwb_property_evidence(dandiset_id: str, property_rows: list[dict[str, Any]]) -> list[Evidence]:
    """Candidate links retain the originating NWB object and file."""
    out = []
    canonical: dict[tuple[str, str, str, Any], dict[str, Any]] = {}
    for row in property_rows:
        if row.get("read_status") not in (None, "Read"):
            continue
        if row.get("evidence_kind") == "NWB table column definition":
            continue
        field = row["property"]
        if field.startswith("column:"):
            continue  # A column definition is not evidence of a populated value.
        value = row.get("value", "")
        if value == "" or str(value).strip().casefold() in PLACEHOLDER_VALUES:
            continue
        canonical_field = (str(row.get("object_path", "")).rsplit("/", 1)[-1]
                           if field == "[scalar]" else field.lstrip("@"))
        key = (str(row.get("asset_id", "")), canonical_field.casefold(),
               str(value).replace(" ", "T", 1) if canonical_field == "date_of_birth" else str(value),
               row.get("row_index"))
        previous = canonical.get(key)
        if previous is None or (str(row.get("object_path", "")).startswith("/") and
                                not str(previous.get("object_path", "")).startswith("/")):
            canonical[key] = row
    for row in canonical.values():
        field = row["property"]
        value = row["value"]
        path = str(row["object_path"]) if field == "[scalar]" else str(row["object_path"]) + "/" + field
        if field == "[scalar]":
            field = str(row["object_path"]).rsplit("/", 1)[-1]
        elif field.startswith("@"):
            field = field[1:]
        if row.get("row_index") is not None:
            path += f'[row {row["row_index"]}]'
        is_narrative = field in {"description", "comments", "notes", "session_description",
                                  "experiment_description", "subject_description", "protocol", "surgery", "virus"}
        ambiguous = field in {"name", "source", "type", "size", "location", "start_time", "end_time", "model"}
        out.append(Evidence(audit_field=field, value=value, source_type="NWB file",
                            source_location=f'{row["asset_path"]}:{path}',
                            asset_id=row["asset_id"],
                            confidence="Low" if is_narrative else "Medium" if ambiguous else "High",
                            review_status="NWB text—review" if is_narrative else "Needs Review" if ambiguous else "NWB structured value"))
        for target, aliases in NWB_FIELD_ALIASES.items():
            if field in aliases:
                out.append(Evidence(audit_field=target, value=value, source_type="NWB alias candidate",
                                    source_location=f'{row["asset_path"]}:{path}',
                                    asset_id=row["asset_id"], confidence="Low" if is_narrative else "Medium",
                                    review_status="Needs Review",
                                    notes=f"Candidate: {field} may describe {target}; verify experimental context."))
    return out

def field_key(value: str) -> str:
    return normalize_field_name(value)


def choose_best_evidence(headers: list[str], evidence: list[Evidence],
                         allowed_fields: set[str] | None = None) -> dict[str, Evidence]:
    by_field: dict[str, list[Evidence]] = defaultdict(list)
    for item in evidence:
        by_field[field_key(item.audit_field)].append(item)

    confidence_rank = {"High": 3, "Medium": 2, "Low": 1, "—": 0}
    source_rank = {
        "NWB file": 6,
        "NWB alias candidate": 5,
    }

    selected: dict[str, Evidence] = {}
    for header in headers:
        candidates = by_field.get(field_key(header), [])
        if allowed_fields is not None and header not in allowed_fields:
            candidates = []
        if field_key(header) in {field_key(f) for f in CONTEXTUAL_FIELDS}:
            candidates = []
        if not candidates:
            selected[header] = Evidence(
                audit_field=header,
                value=NOT_REPORTED,
                source_type="No NWB value extracted",
                confidence="—",
                review_status="Missing",
                notes="No matching populated NWB property in successfully read files; inspect file status and unmapped properties before confirming absence.",
            )
            continue
        candidates.sort(
            key=lambda x: (confidence_rank.get(x.confidence, 0), source_rank.get(x.source_type, 0)),
            reverse=True,
        )
        selected[header] = candidates[0]
    return selected
