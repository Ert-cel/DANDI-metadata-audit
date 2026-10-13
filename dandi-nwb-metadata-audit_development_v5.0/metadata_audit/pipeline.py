from __future__ import annotations

from .config import AuditConfig
from .extractors.dandi import extract_dandiset
from .extractors.nwb import extract_nwb_assets
from .models import AuditResult, Evidence
from .output.workbook import write_master_workbook
from .processing.mapping import nwb_property_evidence
from .processing.modality_detect import classify_detected_modalities
from .project import initialize_project
from dandi.dandiapi import DandiAPIClient


def _dandi_source_records(dandiset_id: str, metadata: dict) -> list[dict]:
    """Preserve landing-page fields as reference evidence with exact JSON paths."""
    out: list[dict] = []
    def visit(value, path: str):
        if isinstance(value, dict):
            for key, child in value.items():
                visit(child, f"{path}.{key}" if path else key)
        elif isinstance(value, list):
            for idx, child in enumerate(value):
                visit(child, f"{path}[{idx}]")
        elif value is not None and str(value).strip():
            display = str(value)
            out.append({"Dandiset ID": dandiset_id, "Asset ID": "",
                        "Audit Field": path.rsplit(".", 1)[-1],
                        "Extracted Value": display[:32000],
                        "Source Type": "DANDI landing page", "Source Location": path,
                        "Supporting Text": "", "Review Status": "Reference only",
                        "Notes": "Does not establish that this value is stored in an NWB file." +
                                 (" Value truncated at 32,000 characters." if len(display) > 32000 else ""),
                        "Evidence Role": "DANDI reference"})
    visit(metadata, "")
    return out


def run_audit(config: AuditConfig):
    initialize_project(config)
    result = AuditResult()

    # 1. DANDI archive metadata and asset inventory.
    # Keep the DANDI client alive while RemoteAsset URLs are resolved.
    with DandiAPIClient() as client:
        result.dandiset_metadata, result.asset_rows, nwb_assets = extract_dandiset(config, client)
        result.dandi_reference_rows = _dandi_source_records(config.dandiset_id, result.dandiset_metadata)

        # 2. Structured metadata inside NWB files.
        result.nwb_rows, result.nwb_object_rows, result.electrode_rows, result.nwb_property_rows, matching_rows = extract_nwb_assets(config, nwb_assets)
    successful = sum(row.get("extraction_status") == "Success" for row in result.nwb_rows)
    failed = sum(row.get("extraction_status") == "Failed" for row in result.nwb_rows)
    # Still write file failures and blank requirement values for a failed pilot.

    # DANDI resources are references only; they are never requirement values.
    for item in result.dandiset_metadata.get("relatedResource", []) or []:
        result.associated_resources.append({
            "Dandiset ID": config.dandiset_id, "Name": item.get("name", ""),
            "Relationship": item.get("relation", ""), "Identifier": item.get("identifier", ""),
            "URL": item.get("url", ""), "Source": "DANDI landing-page metadata",
        })
    detected = classify_detected_modalities({}, result.nwb_rows, result.nwb_object_rows)
    result.modality_classification = {
        "primary_modality": detected.get("primary_modality", "Other / unclassified"),
        "detected_modalities": detected.get("all_modalities", []),
        "agreement": "NWB-only classification",
    }
    result.evidence.extend(nwb_property_evidence(config.dandiset_id, matching_rows))
    if successful and detected.get("all_modalities"):
        result.evidence.append(Evidence(
            audit_field="modalities", value="; ".join(detected["all_modalities"]),
            source_type="NWB-derived", source_location="NWB Objects: neurodata_type",
            confidence="Medium", review_status="Needs Review",
            notes="Derived from observed NWB object types; verify per-file modality."))

    output = write_master_workbook(config, result)
    return output, successful, failed
