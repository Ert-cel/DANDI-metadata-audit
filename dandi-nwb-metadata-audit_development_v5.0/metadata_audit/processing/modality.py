from __future__ import annotations


def audit_sheet_for_modality(primary: str) -> str:
    text = (primary or "").lower()
    if "fiber photometry" in text:
        return "Fiber Photometry Audit"
    if "calcium imaging" in text:
        return "Calcium Imaging Audit"
    if "ephys" in text or "electrophysiology" in text:
        return "Ephys Audit"
    return "Other Modalities Audit"
