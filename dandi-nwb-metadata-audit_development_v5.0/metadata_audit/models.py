from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Evidence:
    audit_field: str
    value: Any
    source_type: str
    source_location: str = ""
    confidence: str = "Medium"
    supporting_text: str = ""
    review_status: str = "Needs Review"
    notes: str = ""
    asset_id: str = ""
    doi: str = ""
    pmid: str = ""
    pmcid: str = ""

    def as_dict(self, dandiset_id: str) -> dict[str, Any]:
        return {
            "Dandiset ID": dandiset_id,
            "Asset ID": self.asset_id,
            "Audit Field": self.audit_field,
            "Extracted Value": self.value,
            "Source Type": self.source_type,
            "Source Location": self.source_location,
            "Supporting Text": self.supporting_text,
            "Confidence": self.confidence,
            "Review Status": self.review_status,
            "DOI": self.doi,
            "PMID": self.pmid,
            "PMCID": self.pmcid,
            "Notes": self.notes,
        }


@dataclass(slots=True)
class AuditResult:
    dandiset_metadata: dict[str, Any] = field(default_factory=dict)
    asset_rows: list[dict[str, Any]] = field(default_factory=list)
    nwb_rows: list[dict[str, Any]] = field(default_factory=list)
    nwb_object_rows: list[dict[str, Any]] = field(default_factory=list)
    nwb_property_rows: list[dict[str, Any]] = field(default_factory=list)
    associated_resources: list[dict[str, Any]] = field(default_factory=list)
    dandi_reference_rows: list[dict[str, Any]] = field(default_factory=list)
    electrode_rows: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    modality_classification: dict[str, Any] = field(default_factory=dict)
