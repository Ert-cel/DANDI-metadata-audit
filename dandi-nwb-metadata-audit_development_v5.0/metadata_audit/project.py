from __future__ import annotations

import importlib.util
import logging
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .config import AuditConfig

REQUIRED_PACKAGES = (
    "dandi",
    "pynwb",
    "remfile",
    "h5py",
    "openpyxl",
)


def initialize_project(config: AuditConfig, *, announce: bool = False) -> list[Path]:
    """Create every runtime directory required by the audit engine.

    The function is safe to call before every run. Existing directories are
    preserved and missing directories are created recursively.
    """
    directories = [
        config.output_directory,
        config.output_directory / "archive",
        config.master_workbook.parent,
        config.cache_directory,
        Path("logs"),
        config.template_path.parent,
    ]

    created: list[Path] = []
    for directory in directories:
        directory = Path(directory)
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            created.append(directory)

    if announce:
        if created:
            print("Preparing project folders...")
            for directory in created:
                print(f"  Created: {directory}")
        else:
            print("Project folders are ready.")

    return created


def configure_logging(log_directory: Path = Path("logs")) -> tuple[logging.Logger, Path]:
    """Configure console and file logging for the current process."""
    log_directory.mkdir(parents=True, exist_ok=True)
    log_path = log_directory / f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logger = logging.getLogger("dandi_metadata_audit")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console_handler)

    return logger, log_path


def doctor_report(config: AuditConfig) -> tuple[bool, list[str]]:
    """Check the local installation and report actionable problems."""
    messages: list[str] = []
    healthy = True

    initialize_project(config)

    for package in REQUIRED_PACKAGES:
        available = importlib.util.find_spec(package) is not None
        messages.append(f"[{'OK' if available else 'MISSING'}] Python package: {package}")
        healthy = healthy and available

    template_exists = config.template_path.exists()
    messages.append(
        f"[{'OK' if template_exists else 'MISSING'}] Master template: {config.template_path}"
    )
    healthy = healthy and template_exists

    writable_targets: Iterable[Path] = (
        config.output_directory,
        config.cache_directory,
        Path("logs"),
    )
    for directory in writable_targets:
        probe = directory / ".write_test"
        try:
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            messages.append(f"[OK] Writable directory: {directory}")
        except OSError as exc:
            messages.append(f"[ERROR] Directory is not writable: {directory} ({exc})")
            healthy = False

    return healthy, messages
