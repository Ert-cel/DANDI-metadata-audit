# DANDI/NWB Metadata Audit Engine

**Author:** Celine Ertekin  
**Shared project snapshot:** v5.0  
**Status:** Development / review build; further validation required

A Python workflow for inspecting neuroscience datasets hosted on DANDI and organizing metadata extracted from Neurodata Without Borders (NWB) files into an Excel audit workbook and a compressed property inventory.

This project supports review of metadata relevant to electrophysiology, fiber photometry, and calcium imaging. It records evidence locations and separates information stored inside NWB files from dataset-level DANDI references. Automated findings support human review; they are not a complete or authoritative assessment of dataset quality.

## Version identity and relationship to the original audit

This repository contains the newer engine supplied as `DANDI_NWB_Audit_Engine_v5.0.zip`. It is intended to support more thorough NWB metadata extraction. The older engine used for the completed metadata audit is **not included** in this package. Findings from that earlier audit should not be attributed to this development snapshot without rerunning and validating it.

The original files contain inherited version labels:

| Location | Existing label | Meaning in this repository |
| --- | --- | --- |
| Supplied archive name | v5.0 | Name of the shared project snapshot |
| `pyproject.toml` | 2.0.0 | Preserved package-distribution version |
| `metadata_audit/__init__.py` | 1.4.0 | Preserved module version constant |
| Historical changelog | 2.0.0 and earlier | Original development notes |

All Python source files, dependency specifications, workbook templates, and the field catalog have been preserved byte for byte. These labels have not been changed inside the code. v5.0 is a snapshot label, not a claim that the installed Python package reports version 5.0.0.

The supplied documentation states that a previous pilot inspected one of 56 NWB assets in Dandiset 001177 and encountered 71 unresolved HDF5 references. The revised scanner includes reference-resolution changes, but that documentation also states that it had not been rerun against DANDI in that environment. Those historical observations do not establish the performance of this snapshot. This snapshot still requires live DANDI validation.

## What the engine does

1. Uses the DANDI API to locate a Dandiset, its selected version, NWB assets, dataset metadata, and associated-resource links.
2. Uses remote file access through `remfile`, PyNWB, and HDF5 inspection to examine NWB objects and metadata.
3. Collects scalar metadata, object information, DynamicTable metadata cells, HDF5 attributes, scalar datasets, and array shape/type inventories.
4. Records property paths and read status, including failures and flagged truncation.
5. Matches extracted NWB metadata against a modality-aware field catalog for review.
6. Writes an Excel workbook and a compressed JSON Lines inventory.

DANDI landing-page values are labeled as reference information. They do not establish that those values are stored inside NWB files. Narrative matches, alias candidates, and inferred modality labels require review.

## What this snapshot does not do

- It does not scrape publication text, CatalystNeuro pages, or usage statistics. Associated-resource links are collected for reference.
- It does not export complete signal arrays, movies, waveforms, pixel masks, or spike-time vectors. Large arrays are inventoried by shape and data type.
- It does not guarantee that every NWB extension or ragged table can be fully interpreted.
- It does not establish dataset-wide absence of a field when files are unscanned, values are unreadable, or no mapping match is found.
- It does not replace direct inspection, experiment-context review, or the earlier manual audit.

## Repository contents

| Path | Purpose |
| --- | --- |
| `run_audit.py` | Entry point for running the command-line workflow from this repository |
| `metadata_audit/` | Python package, extraction, mapping, workbook generation, and field catalog |
| `templates/Metadata_Audit_Master_Template.xlsx` | Default template required by the command-line workflow |
| `templates/ASAP_NWB_Metadata_Audit_Template_v5.xlsx` | Additional source-labeled audit template supplied with the project |
| `pyproject.toml` | Python requirements, package metadata, and command-line entry point |
| `requirements.txt` | Editable-install shortcut: `-e .` |
| `tests/` | Existing regression tests |
| `START_HERE.md` | Short pilot-review checklist |
| `CORE_WORKFLOW.md` | Description of the implemented workflow |
| `CHANGELOG.md` | Preserved historical development notes |

The engine creates `outputs/`, `outputs/archive/`, `cache/remfile/`, and `logs/` as needed. Do not rename the Python package or required templates unless you also update their code references. Run commands from the repository root, where `run_audit.py` and `templates/` are located.

## Requirements

- Python **3.10 or newer**, as declared in the supplied package configuration.
- Internet access to DANDI and the storage serving the NWB assets.
- A writable working directory and sufficient local space for cache, logs, and outputs.
- Excel or another compatible spreadsheet viewer to review the workbook.

The installation declares `dandi>=0.68`, `pynwb>=3.0`, `remfile>=0.1.13`, `h5py>=3.10`, and `openpyxl>=3.1`. The optional development dependencies include `pytest>=8`.

Dependencies use lower bounds rather than an exact lock file. A new installation may resolve different versions over time. For a reproducible audit, record the versions you actually used. This project is designed to be run from a checked-out or extracted repository because the default template path is relative to the working directory.

## Installation on Windows (PowerShell)

Download and extract this repository, or clone it using Git. Open PowerShell inside `dandi-nwb-metadata-audit`, the folder containing `run_audit.py`.

```powershell
# Confirm Python is available
py --version

# Create an isolated Python environment
py -m venv .venv

# Install the engine and its existing test dependencies
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

# Check required packages, template availability, and writable folders
.\.venv\Scripts\python.exe run_audit.py doctor

# Display the available audit options
.\.venv\Scripts\python.exe run_audit.py audit --help
```

These examples call the environment's Python executable directly, so activating PowerShell scripts is unnecessary. If your default Python is older than 3.10, choose an installed compatible interpreter when creating the environment, for example `py -3.11 -m venv .venv` if Python 3.11 is installed.

## Installation on macOS or Linux

From the repository root:

```bash
python3 --version
python3 -m venv .venv
./.venv/bin/python -m pip install -e ".[dev]"
./.venv/bin/python run_audit.py doctor
./.venv/bin/python run_audit.py audit --help
```

The following run examples use Windows executable paths. On macOS/Linux, replace `.\.venv\Scripts\python.exe` with `./.venv/bin/python`.

## Start with a pilot

Use a new output workbook, separate from your completed audit or any older mixed-source master workbook.

```powershell
.\.venv\Scripts\python.exe run_audit.py audit 001177 --max-assets 3 --master-workbook outputs/NWB_Audit_Pilot.xlsx
```

This scans at most the first three NWB assets in path order. It is not a random or representative sample. The default DANDI version is `draft`, which can change over time.

Before interpreting the pilot:

1. Check the total asset count, scanned count, failed files, and property-read errors.
2. Inspect the same scanned files directly using PyNWB, Neurosift, or another suitable NWB viewer.
3. Compare exact NWB object paths and values with the workbook findings.
4. Review source roles so DANDI references are not mistaken for NWB evidence.
5. Establish which experimental conditions and modalities apply before interpreting blanks.
6. Resolve material discrepancies before attempting a full audit.

## Pin a DANDI version

For reproducible analysis, choose an actual published version listed for the Dandiset and pass it with `--version`. Replace the placeholder below before running:

```powershell
.\.venv\Scripts\python.exe run_audit.py audit 001177 --version "REPLACE_WITH_PUBLISHED_VERSION" --max-assets 3 --master-workbook outputs/NWB_Audit_Pinned_Pilot.xlsx
```

The engine snapshot version and the DANDI dataset version are different identifiers. Record both.

## Run a full audit

After validating the pilot, omit `--max-assets` to attempt all NWB assets in the selected Dandiset version:

```powershell
.\.venv\Scripts\python.exe run_audit.py audit 001177 --version "REPLACE_WITH_PUBLISHED_VERSION" --master-workbook outputs/NWB_Audit_Full.xlsx
```

Runtime and cache requirements depend on file count, metadata complexity, remote access, and connection speed. No fixed runtime or memory guarantee is provided.

## Audit multiple Dandisets

Pass multiple IDs to accumulate results into one workbook:

```powershell
.\.venv\Scripts\python.exe run_audit.py audit 001177 001538 001777 --max-assets 3 --master-workbook outputs/NWB_Audit_Batch_Pilot.xlsx
```

The asset limit applies separately to each Dandiset. Alternatively, create a plain-text file named `dandiset_ids.txt`, with one ID per line. Blank lines and lines beginning with `#` are ignored:

```text
# Example pilot batch
001177
001538
001777
```

```powershell
.\.venv\Scripts\python.exe run_audit.py audit --ids-file dandiset_ids.txt --max-assets 3 --master-workbook outputs/NWB_Audit_Batch_Pilot.xlsx
```

A supplied `--version` applies to every ID in that command. If the datasets require different published version identifiers, run separate commands with the appropriate identifier for each.

## Command-line options

| Command or option | Purpose / default |
| --- | --- |
| `doctor` | Checks required packages, template existence, and directory write access; does not validate live extraction |
| `init` | Creates runtime folders; use `doctor` to check template availability |
| `audit ID [ID ...]` | Audits one or more Dandisets |
| `--ids-file PATH` | Adds IDs from a text file |
| `--version VALUE` | DANDI version; default `draft` |
| `--max-assets N` | Positive per-Dandiset pilot limit; omitted means attempt all NWB assets |
| `--master-workbook PATH` | Output workbook; default `outputs/Metadata_Audit_Master.xlsx` |
| `--template PATH` | Default `templates/Metadata_Audit_Master_Template.xlsx` |
| `--cache-directory PATH` | Remote-file disk cache; default `cache/remfile` |
| `--audit-sheet VALUE` | Default `auto`; explicit choices: `Ephys Audit`, `Fiber Photometry Audit`, `Calcium Imaging Audit`, `Other Modalities Audit` |
| `--no-backup` | Disables the default backup of an existing workbook |

For a custom template, preserve the structure and sheet names the engine expects. Arbitrary workbooks are not interchangeable with the supplied master template. A manually selected audit sheet controls placement; it does not prove the dataset has that modality.

## Outputs and how to read them

| Output | What it contains |
| --- | --- |
| Selected `.xlsx` workbook | Audit fields, source evidence, dataset inventories, and review tables |
| `NWB_Properties_<Dandiset ID>.jsonl.gz` | Compressed inventory of collected property records, including records beyond the Excel preview; subject to extraction limits and flagged truncation |
| `logs/audit_<timestamp>.log` | Run log; also retain terminal output for detailed extraction messages |
| `<workbook parent>/archive/` | Timestamped backups of an existing workbook, unless disabled |
| `cache/remfile/` | Local cache used for remote NWB access, unless overridden |

The compressed inventory is written beside the chosen workbook. Each line is one JSON record. It is not a copy of the full NWB file or a raw signal export.

Important workbook tabs include:

| Tab | Use |
| --- | --- |
| `Dataset Inventory` | Compare available and inspected assets, failures, and inspection status |
| `NWB File Metadata` | Check individual files and extraction/read status |
| `NWB Findings` | Review compact subject, session, device, electrode, and recording findings |
| `Common Data Elements` | Review requirements relevant to modalities observed in scanned assets |
| `Requirement Review` | Inspect requirement candidates and evidence for human review |
| `Source Records` | Review grouped NWB values and separately labeled DANDI references |
| `NWB Properties` | Inspect detailed metadata paths and technical inventory; preview capped at 50,000 records per Dandiset extraction |
| `NWB Objects` / `Electrode Groups` | Review object and electrode-group inventories |
| `Asset Inventory` | Review available NWB asset records |
| `Dataset Features` | Review observed or inferred experimental features |
| `DANDI Resources` | Find associated-resource references; their content is not scraped |
| `Allen Requirements` / `Field Catalog` | Review the working requirement register |

Check both file-level failures and property-level errors. A file-level success does not imply every metadata property was read. Excel previews and grouped source rows are not substitutes for the complete property inventory.

### Repeated runs and preservation

Close the output workbook in Excel before running. The engine updates records for a Dandiset in an existing workbook rather than treating every rerun as an independent historical result. Backups apply to the workbook, not the compressed property inventory. A rerun using the same output directory and Dandiset ID overwrites that Dandiset's `.jsonl.gz` inventory.

Use distinct output directories for separate pilots, versions, or final runs, such as `outputs/pilot/Review.xlsx` and `outputs/final/Review.xlsx`. Keep copies of the exact inputs, commands, inventories, workbooks, and environment record used for reported results.

## Reproducibility checklist

Record:

- Repository commit or downloaded snapshot identifier.
- Dandiset ID and published DANDI version.
- Exact command and any pilot limit.
- Scanned asset identifiers and paths.
- Python and dependency versions.
- Output workbook, compressed inventory, terminal output, and logs.
- Manual-review decisions and unresolved discrepancies.

To capture installed packages after creating an output directory:

```powershell
.\.venv\Scripts\python.exe -m pip freeze > outputs/environment.txt
```

This records an installed environment; it does not create a tested cross-platform dependency lock.

## Existing tests

With the development dependencies installed:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The supplied tests cover aspects of modality mapping, NWB property inventory, and source separation. They do not establish successful extraction from every Dandiset or extension. These tests do not replace a live DANDI validation run.

## Troubleshooting

| Problem | Action |
| --- | --- |
| `py` or `python3` is not found | Install a compatible Python interpreter, reopen the terminal, and verify its version |
| Missing Python packages | Install using the same environment executable used to run the engine |
| Missing master template | Run from the repository root; retain `templates/Metadata_Audit_Master_Template.xlsx`, or provide its correct path |
| Permission error saving Excel | Close the workbook in Excel; confirm the destination is writable |
| Failed remote file access | Check connectivity and that the requested Dandiset version and assets are accessible; inspect terminal messages and file-level failures |
| NWB extension or property-read errors | Inspect the affected asset directly and review the exact error; targeted extension support or extraction changes may be necessary |
| Blank or `Not Reported` field | Check scan coverage, read errors, source paths, mappings, and experiment context before drawing conclusions |
| Missing modalities in a pilot | Check unscanned assets; a path-ordered pilot may not cover all modalities |
| Expected publication evidence is absent | This snapshot does not retrieve publication text; preserve and review the earlier manual audit separately |

## Attribution, citation, and license

Author: **Celine Ertekin**.

When describing or citing this work, identify the repository URL and exact commit or release used, along with the Dandiset version and analysis methods. A formal citation file can be added once repository and release details are known.

## Reporting issues

Provide the Dandiset ID/version, scanned asset path, exact command, Python/package versions, relevant error, expected behavior, and observed behavior. For mapping discrepancies, include the exact NWB property path. Share a minimal reproducible example and omit private information or credentials.
