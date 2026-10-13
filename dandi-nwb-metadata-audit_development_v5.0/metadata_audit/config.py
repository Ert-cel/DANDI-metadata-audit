from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

NOT_REPORTED = "Not Reported"
MULTIPLE_VALUES = "Multiple values; see source sheets"

@dataclass(slots=True)
class AuditConfig:
    dandiset_id: str
    version: str = "draft"
    master_workbook: Path = Path("outputs/Metadata_Audit_Master.xlsx")
    template_path: Path = Path("templates/Metadata_Audit_Master_Template.xlsx")
    cache_directory: Path = Path("cache/remfile")
    output_directory: Path = Path("outputs")
    max_assets: int | None = None
    audit_sheet: str = "auto"
    keep_backup: bool = True

    def __post_init__(self) -> None:
        self.dandiset_id = str(self.dandiset_id).strip().zfill(6)
        if self.max_assets is not None and self.max_assets <= 0:
            raise ValueError("max_assets must be a positive integer")
        self.master_workbook = Path(self.master_workbook)
        self.template_path = Path(self.template_path)
        self.cache_directory = Path(self.cache_directory)
        self.output_directory = Path(self.output_directory)

    def ensure_directories(self) -> None:
        self.output_directory.mkdir(parents=True, exist_ok=True)
        self.master_workbook.parent.mkdir(parents=True, exist_ok=True)
        self.cache_directory.mkdir(parents=True, exist_ok=True)
        (self.output_directory / "archive").mkdir(parents=True, exist_ok=True)
        Path("logs").mkdir(parents=True, exist_ok=True)
