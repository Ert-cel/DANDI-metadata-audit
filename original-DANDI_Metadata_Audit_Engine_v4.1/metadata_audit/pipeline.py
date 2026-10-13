from __future__ import annotations

from .config import AuditConfig
from .extractors.catalyst import extract_confirmed_pages, fetch_curated_record
from .extractors.dandi import extract_dandiset
from .extractors.narrative import extract_narrative_evidence
from .extractors.nwb import extract_nwb_assets
from .extractors.publication import extract_publications
from .extractors.usage import extract_usage_summary
from .models import AuditResult
from .output.workbook import write_master_workbook
from .processing.mapping import structured_evidence
from .processing.modality import combine_modality_sources
from .project import initialize_project


def run_audit(config: AuditConfig):
    initialize_project(config)
    result = AuditResult()

    # 1. DANDI archive metadata and asset inventory.
    result.dandiset_metadata, result.asset_rows, nwb_assets = extract_dandiset(config)

    # 2. Structured metadata inside NWB files.
    result.nwb_rows, result.nwb_object_rows, result.electrode_rows = extract_nwb_assets(config, nwb_assets)
    successful = sum(row.get("extraction_status") == "Success" for row in result.nwb_rows)
    failed = sum(row.get("extraction_status") == "Failed" for row in result.nwb_rows)
    if successful == 0:
        raise RuntimeError("No NWB files were read successfully.")

    # 3. Curated metadata that powers the CatalystNeuro ASAP usage page.
    result.catalyst_record, catalyst_evidence = fetch_curated_record(config)
    result.evidence.extend(catalyst_evidence)

    # 4. Keep curated modality and NWB-detected modality as separate evidence.
    result.modality_classification = combine_modality_sources(
        result.catalyst_record,
        result.dandiset_metadata,
        result.nwb_rows,
        result.nwb_object_rows,
    )

    # 5. High-confidence structured audit fields.
    result.evidence.extend(structured_evidence(
        config.dandiset_id,
        result.dandiset_metadata,
        result.nwb_rows,
        result.modality_classification,
    ))

    # 6. Conservative narrative extraction from the confirmed DANDI description.
    description = result.dandiset_metadata.get("description") or ""
    title = result.dandiset_metadata.get("name") or ""
    if title or description:
        result.evidence.extend(extract_narrative_evidence(
            text=f"{title}. {description}",
            source_type="DANDI description",
            source_location=f"DANDI:{config.dandiset_id}",
        ))

    # 7. Publication lookup is restricted to DOI values already linked to the Dandiset/NWB.
    result.publication_rows, publication_evidence = extract_publications(
        config,
        result.dandiset_metadata,
        result.nwb_rows,
    )
    result.evidence.extend(publication_evidence)

    # 8. Optional Catalyst project pages are read only when explicitly supplied.
    result.catalyst_page_rows, page_evidence = extract_confirmed_pages(config)
    result.evidence.extend(page_evidence)

    # 9. Headline usage statistics. Detailed usage analysis can be added later.
    if config.collect_usage:
        result.usage_summary = extract_usage_summary(config)

    output = write_master_workbook(config, result)
    return output, successful, failed
