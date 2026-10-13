from __future__ import annotations

import argparse
import traceback
from pathlib import Path

from .config import AuditConfig
from .project import configure_logging, doctor_report, initialize_project


def _read_ids(path: str | None) -> list[str]:
    if not path:
        return []
    return [
        line.strip()
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dandi-metadata-audit",
        description="NWB-only evidence review engine; DANDI identifies files and associated resources.",
    )
    sub = parser.add_subparsers(dest="command")

    audit = sub.add_parser("audit", help="Audit one or more Dandisets into one master workbook.")
    audit.add_argument("dandiset_ids", nargs="*", help="One or more Dandiset IDs.")
    audit.add_argument("--ids-file", help="Text file with one Dandiset ID per line.")
    audit.add_argument("--version", default="draft")
    audit.add_argument("--master-workbook", default="outputs/Metadata_Audit_Master.xlsx")
    audit.add_argument("--template", default="templates/Metadata_Audit_Master_Template.xlsx")
    audit.add_argument("--cache-directory", default="cache/remfile")
    audit.add_argument("--max-assets", type=int, default=None, help="Pilot with only the first N NWB files.")
    audit.add_argument(
        "--audit-sheet",
        choices=["auto", "Ephys Audit", "Fiber Photometry Audit", "Calcium Imaging Audit", "Other Modalities Audit"],
        default="auto",
    )
    audit.add_argument("--no-backup", action="store_true")

    init = sub.add_parser("init", help="Create runtime folders and verify the template.")
    init.add_argument("--master-workbook", default="outputs/Metadata_Audit_Master.xlsx")
    init.add_argument("--template", default="templates/Metadata_Audit_Master_Template.xlsx")
    init.add_argument("--cache-directory", default="cache/remfile")

    doctor = sub.add_parser("doctor", help="Check packages, folders, permissions, and template.")
    doctor.add_argument("--master-workbook", default="outputs/Metadata_Audit_Master.xlsx")
    doctor.add_argument("--template", default="templates/Metadata_Audit_Master_Template.xlsx")
    doctor.add_argument("--cache-directory", default="cache/remfile")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    if args.command in {"init", "doctor"}:
        config = AuditConfig(
            dandiset_id="000000",
            master_workbook=Path(args.master_workbook),
            template_path=Path(args.template),
            cache_directory=Path(args.cache_directory),
            output_directory=Path(args.master_workbook).parent,
        )
        initialize_project(config, announce=True)
        if args.command == "doctor":
            healthy, messages = doctor_report(config)
            print("\nEnvironment check:")
            for message in messages:
                print(f"  {message}")
            raise SystemExit(0 if healthy else 1)
        return

    ids = list(args.dandiset_ids) + _read_ids(args.ids_file)
    ids = list(dict.fromkeys(str(value).strip().zfill(6) for value in ids if str(value).strip()))
    if not ids:
        raise SystemExit("No Dandiset IDs were supplied.")

    from .pipeline import run_audit

    logger, log_path = configure_logging()
    logger.info(f"Run log: {log_path.resolve()}")
    completed: list[str] = []
    failed: list[str] = []

    for index, dandiset_id in enumerate(ids, 1):
        print("\n" + "=" * 72)
        print(f"[{index}/{len(ids)}] Auditing Dandiset {dandiset_id}")
        print("=" * 72)
        config = AuditConfig(
            dandiset_id=dandiset_id,
            version=args.version,
            master_workbook=Path(args.master_workbook),
            template_path=Path(args.template),
            cache_directory=Path(args.cache_directory),
            output_directory=Path(args.master_workbook).parent,
            max_assets=args.max_assets,
            audit_sheet=args.audit_sheet,
            keep_backup=not args.no_backup,
        )
        try:
            output, successful, n_failed = run_audit(config)
            print(f"Updated master workbook: {output.resolve()}")
            print(f"Successfully read {successful} NWB files; {n_failed} failed.")
            completed.append(dandiset_id)
        except KeyboardInterrupt:
            print("\nAudit cancelled.")
            raise SystemExit(1)
        except Exception as error:
            print(f"Dandiset {dandiset_id} failed: {type(error).__name__}: {error}")
            traceback.print_exc()
            failed.append(dandiset_id)

    print("\nBatch complete.")
    print("Completed:", ", ".join(completed) or "None")
    print("Failed:   ", ", ".join(failed) or "None")
    if failed:
        raise SystemExit(1)
