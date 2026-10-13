# DANDI Metadata Audit Engine — v4.1

**Author:** Celine Ertekin  
**Project version:** v4.1  
**Status:** Internship development snapshot; this supplied version has not been run

A Python metadata-audit workflow developed during an internship with the Coalition for Aligning Science (CAS), supporting the Aligning Science Across Parkinson's (ASAP) Initiative. The project combines public neuroscience dataset metadata with source-linked evidence to support review of reporting completeness and data reuse.

The workflow is designed to inspect DANDI datasets, selected Neurodata Without Borders (NWB) metadata, CatalystNeuro curated records, associated publications, and optional confirmed project pages. It organizes candidate findings into an Excel audit workbook, with an emphasis on electrophysiology and additional sheets for fiber photometry, calcium imaging, and other modalities.

**This snapshot has not been run, and its outputs have not been validated.** It documents internship development work. It should not be described as the verified executable that generated completed internship findings. The examples below are instructions for future validation, not evidence of completed runs.

## Version identity

The project version for this shared snapshot is **v4.1**, as identified by the author. The supplied archive was named `DANDI_Metadata_Audit_Engine_v1.5_Ephys_Focus(3).zip`; its older internal labels are preserved to keep the code unchanged.

| Location | Preserved label |
| --- | --- |
| Project documentation and shared package | v4.1 |
| `pyproject.toml` distribution version | 1.5.0 |
| `metadata_audit/__init__.py` module constant | 1.4.0 |
| Historical changelog and some request headers | Earlier development labels |

The snapshot label does not mean that installed package metadata reports version 4.1. All Python source, dependencies, tests, and the Excel template are unchanged from the uploaded package.

## Relationship to v5.0

| v4.1: internship development snapshot | v5.0: newer NWB development snapshot |
| --- | --- |
| Combines several public-source types | Focuses on more detailed NWB metadata inspection, with DANDI references |
| Includes linked-publication lookup and narrative candidate extraction | Does not retrieve publication text in its implemented workflow |
| Reads selected NWB fields and top-level object information | Adds more extensive nested-property and HDF5 inventory work |
| Includes CatalystNeuro curated records and headline usage summaries | Emphasizes NWB source separation and requirement review |

v5.0 is a separate development effort intended to improve NWB extraction. This package contains v4.1 only; it does not establish a measured performance comparison between the versions.

## Implemented workflow

The code attempts the following steps for each Dandiset:

1. **DANDI API:** retrieve metadata and an asset inventory for the requested version.
2. **NWB metadata:** use `remfile`, HDF5, and PyNWB to read selected subject, session, device, electrode-group, acquisition, stimulus, processing-module, and analysis information.
3. **CatalystNeuro curated records:** retrieve the configured ASAP dataset YAML and locate the matching dataset record.
4. **Modality comparison:** retain the curated Catalyst modality and modalities inferred from DANDI metadata/NWB object information as separate classifications.
5. **Structured evidence mapping:** map selected values to audit fields, preserving source and confidence information.
6. **DANDI narrative:** extract review candidates from the dataset title and description.
7. **Associated publications:** find DOIs already linked in DANDI or NWB metadata, query Crossref/PubMed/PMC, and extract candidates from available article sections.
8. **Optional confirmed pages:** read the URLs explicitly supplied using `--catalyst-url`.
9. **Usage summaries:** attempt retrieval of headline DANDI access statistics, unless disabled.
10. **Workbook generation:** populate the master audit workbook and source-review tables.

Publication extraction selects sections whose titles resemble methods, recording, surgery, animals, or related experimental topics. If no such sections match, the code falls back to available sections. Publication candidates therefore need direct source review; they are not guaranteed to originate from a narrowly defined Methods section.

The engine does not discover arbitrary project pages through broad web search. The curated YAML is fetched automatically; optional project-page URLs must be supplied explicitly.

## Requirements

- Python **3.10 or newer**, according to the supplied package configuration.
- Internet access to DANDI, remote NWB storage, configured curated metadata/usage sources, Crossref, and NCBI services.
- A writable working directory and sufficient space for the remote-file cache and outputs.
- Excel or a compatible workbook viewer for manual review.

Declared dependencies are `dandi>=0.68`, `pynwb>=3.0`, `remfile>=0.1.13`, `h5py>=3.10`, `pandas>=2.0`, `openpyxl>=3.1`, `requests>=2.31`, `beautifulsoup4>=4.12`, `lxml>=5.0`, and `PyYAML>=6.0`. The development extra includes `pytest>=8`.

These lower-bound requirements are not an exact dependency lock. Record the resolved environment used for any future validated analysis. External services and file formats can change independently of this snapshot.

## Files and folders

| Path | Purpose |
| --- | --- |
| `run_audit.py` | Command-line entry point |
| `metadata_audit/` | Extractors, source mapping, modality handling, and workbook generation |
| `templates/Metadata_Audit_Master_Template.xlsx` | Required default master template |
| `config/` | Supplied configuration notes; the runtime defaults are defined in the Python configuration module |
| `tests/` | Existing mapping, narrative, and modality tests |
| `pyproject.toml` | Package configuration and dependencies |
| `requirements.txt` | Editable-install shortcut (`-e .`) |
| `START_HERE.md` | Pilot checklist |
| `CORE_WORKFLOW.md` | Workflow overview |
| `CHANGELOG.md` | Snapshot identity note and preserved historical changes |

Runtime cache, output, and log folders are created when needed. Keep the internal package, script, and required template filenames unchanged. Run commands from the folder containing `run_audit.py` and `templates/` so relative paths resolve correctly.

## Windows setup (PowerShell)

Open PowerShell inside `original-audit-engine-v4.1`:

```powershell
# Check that Python is installed
py --version

# Create an isolated environment
py -m venv .venv

# Install the engine and its existing test dependencies
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

# Check package availability, template existence, and writable directories
.\.venv\Scripts\python.exe run_audit.py doctor

# Inspect the supported options
.\.venv\Scripts\python.exe run_audit.py audit --help
```

No environment activation or PowerShell execution-policy change is required for these commands. If your default Python is older than 3.10, select an installed compatible interpreter, for example `py -3.11 -m venv .venv` when Python 3.11 is available.

`doctor` checks local installation conditions. It does not demonstrate that network access, source retrieval, metadata mapping, or workbook generation works end to end.

## macOS/Linux setup

From the project root:

```bash
python3 --version
python3 -m venv .venv
./.venv/bin/python -m pip install -e ".[dev]"
./.venv/bin/python run_audit.py doctor
./.venv/bin/python run_audit.py audit --help
```

For the examples below, replace `.\.venv\Scripts\python.exe` with `./.venv/bin/python` on macOS/Linux.

## First pilot

Close Excel and use a fresh workbook separate from completed internship analysis files:

```powershell
.\.venv\Scripts\python.exe run_audit.py audit 001177 --max-assets 3 --master-workbook outputs/pilot/Metadata_Audit_Pilot.xlsx
```

This attempts the first three NWB assets in path order, not a random or representative sample. Use positive asset limits. The default DANDI version is `draft`, which can change over time.

The pipeline stops for a Dandiset if no selected NWB file is successfully read. In that case, the final workbook is not written for that Dandiset. Retain terminal output and logs to diagnose the failure.

## Validation before a full run

1. Check every scanned file's status and error in `NWB File Metadata`.
2. Compare selected values against the same NWB files using an independent reader or viewer.
3. Verify each source location and supporting sentence in `Source Records`.
4. Confirm that structured DANDI/Catalyst values are not presented as proof that metadata exists inside NWB.
5. Check the curated and detected modalities and their agreement status.
6. Inspect publication candidates in the actual linked article and confirm that the reported methods apply to the audited data.
7. Resolve discrepancies before treating any output as a result.

The inherited validation notes focus on checking acquisition versus analysis software, probe models, and surgical versus terminal anaesthesia. For example, review whether Plexon Offline Sorter is kept separate from acquisition equipment, whether Clampex/pCLAMP is excluded from probe models, and whether perfusion anaesthesia is distinguished from surgical anaesthesia. These are validation targets, not confirmed outcomes for this unrun snapshot.

## Pin a dataset version and run all assets

Choose an actual published version for the Dandiset and replace the placeholder:

```powershell
# Validate a pilot with a fixed dataset version first
.\.venv\Scripts\python.exe run_audit.py audit 001177 --version "REPLACE_WITH_PUBLISHED_VERSION" --max-assets 3 --master-workbook outputs/pinned-pilot/Review.xlsx

# After validation, omit the asset limit to attempt all NWB assets
.\.venv\Scripts\python.exe run_audit.py audit 001177 --version "REPLACE_WITH_PUBLISHED_VERSION" --master-workbook outputs/full/Review.xlsx
```

The project version v4.1 and a published DANDI version are different identifiers. Record both. A full run may be slow or require substantial cache space; no runtime guarantee is provided.

## Batch runs

```powershell
.\.venv\Scripts\python.exe run_audit.py audit 001177 001538 001777 --max-assets 3 --master-workbook outputs/batch-pilot/Review.xlsx
```

The limit applies separately to each Dandiset. Alternatively, create `dandiset_ids.txt` with one ID per line; blank lines and lines beginning with `#` are ignored:

```powershell
.\.venv\Scripts\python.exe run_audit.py audit --ids-file dandiset_ids.txt --max-assets 3 --master-workbook outputs/batch-pilot/Review.xlsx
```

One `--version` value applies to all datasets in that command. Use separate commands for datasets with different published version identifiers. Likewise, explicitly supplied `--catalyst-url` values apply to each dataset in a batch; provide dataset-specific pages in separate commands to avoid associating unrelated page evidence with other datasets.

## Optional settings

| Option | Meaning / default |
| --- | --- |
| `--version VALUE` | DANDI version; default `draft` |
| `--max-assets N` | Per-Dandiset pilot limit; omitted means attempt all NWB assets |
| `--master-workbook PATH` | Default `outputs/Metadata_Audit_Master.xlsx` |
| `--template PATH` | Default `templates/Metadata_Audit_Master_Template.xlsx` |
| `--cache-directory PATH` | Default `cache/remfile` |
| `--ids-file PATH` | Additional IDs from a plain-text file |
| `--audit-sheet VALUE` | Default `auto`; explicit choices are `Ephys Audit`, `Fiber Photometry Audit`, `Calcium Imaging Audit`, and `Other Modalities Audit` |
| `--catalyst-url URL` | Explicitly supplied project page; may be repeated |
| `--contact-email ADDRESS` | Contact used in the publication-service request header |
| `--no-usage` | Skip usage-summary retrieval |
| `--no-backup` | Disable automatic backup of an existing workbook |

For an explicitly confirmed CatalystNeuro page, replace the placeholder with the actual URL:

```powershell
.\.venv\Scripts\python.exe run_audit.py audit 001177 --max-assets 3 --catalyst-url "REPLACE_WITH_CONFIRMED_PAGE_URL" --no-usage --master-workbook outputs/page-pilot/Review.xlsx
```

Custom templates must retain the structure expected by the code. Choosing an audit sheet manually controls placement; it does not establish the underlying modality.

## Workbook outputs

| Tab | Purpose |
| --- | --- |
| `Dataset Inventory` | Dataset summary, modality comparison, and scan information |
| `Ephys Audit` | Electrophysiology audit fields |
| `Fiber Photometry Audit` | Fiber photometry audit fields |
| `Calcium Imaging Audit` | Calcium imaging audit fields |
| `Other Modalities Audit` | Other modality audit fields |
| `Dataset Features` | Features, sources, confidence, and review information |
| `Common Data Elements` | Summary of selected audit values |
| `Source Records` | Structured and narrative evidence with source information |
| `Publication Candidates` | Review candidates extracted from available linked-publication sections |
| `NWB File Metadata` | Selected file-level metadata, extraction status, and errors |
| `Usage Summary` | Headline usage-statistics retrieval results |

The code collects asset and object information internally, but this version does not export the v5.0-style comprehensive `NWB Properties` inventory or compressed JSONL property sidecar. Do not expect v5.0 output tables in v4.1.

Outputs are accumulated in the selected workbook. Repeated runs replace dataset-specific records in several tables; they are not independent historical records. Existing workbook backups are stored in an `archive/` folder beside the selected workbook, unless disabled. Runtime messages and errors appear in the terminal, and run logs are stored in `logs/`.

Use separate output paths for distinct pilots and analyses. Do not run this engine over an irreplaceable manually reviewed workbook; the writer updates and removes sheets as part of its workflow.

## Interpretation and limitations

- **Structured Evidence** identifies a structured source. It can come from DANDI or curated metadata as well as NWB; always inspect the source type.
- **Needs Manual Review** identifies candidates extracted from prose or otherwise requiring review. Confirm the exact supporting sentence and experimental context.
- **Not Reported** means the engine did not find a mapped value in the sources it inspected. It does not prove the information was never collected or is absent everywhere in a dataset.
- The inherited workbook label **Complete** is assigned when no asset limit is supplied. It is not proof that all files were successfully read or that review is complete. Inspect file failures and source coverage directly.
- When a curated Catalyst modality exists, it normally controls automatic sheet placement. Otherwise, the engine uses the detected classification. Disagreements are retained for review.
- Linked-publication lookup depends on DOI discovery, service responses, and accessible PMC text. Relevant material can be missing or unmatched.
- Selected NWB fields and top-level object inspection do not cover every nested object, DynamicTable, extension, or experimental detail.
- Usage summaries can be unavailable or empty. An empty parsed summary is not definitive evidence of zero dataset use.
- Fixed remote source URLs and unpinned dependencies require validation in the environment where the engine will be used.

## Tests and reproducibility

Run the supplied tests after installing the development dependencies:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The existing tests concern narrative extraction, mapping, and modality behavior. Passing them would not establish successful live extraction or complete audit coverage.

For each future validated run, retain the project snapshot/commit, Dandiset ID/version, exact command, scanned asset paths, Python/dependency versions, source retrieval date, workbook, terminal output, logs, and manual-review decisions. After creating an output directory, capture the installed environment with:

```powershell
.\.venv\Scripts\python.exe -m pip freeze > outputs/environment.txt
```

Local packaging checks verified unchanged source files, Python syntax, and command-line help. They did not run an audit against live services or validate scientific results.

## Troubleshooting

| Problem | Action |
| --- | --- |
| Python command is unavailable | Install a compatible interpreter and reopen the terminal |
| Missing packages | Install with the same environment executable used to run the engine |
| Missing template | Run from the project root or supply the correct template path |
| Workbook cannot be saved | Close it in Excel and check directory permissions |
| No NWB files were successfully read | Inspect terminal/file errors and remote access; the pipeline will stop before writing that dataset's workbook results |
| Catalyst metadata or usage warning | Check terminal messages; review whether the remote source was retrieved and parsed successfully |
| Publication candidates are missing | Check linked DOIs, publication-service errors, and PMC text availability |
| Incorrect narrative candidate | Verify supporting text and context manually; a rule match is not a verified finding |
| Blank or `Not Reported` field | Review scan coverage, read failures, mappings, and all relevant public sources |
| Unexpected audit-sheet placement | Compare curated and detected modalities; inspect the agreement status |

## Attribution, citation, and license

Author: **Celine Ertekin**.

When describing or citing this work, identify the repository URL and exact commit or release used, along with the Dandiset version and analysis methods. A formal citation file can be added once repository and release details are known.

## Reporting issues

Provide the Dandiset ID/version, scanned asset path, exact command, Python/package versions, relevant error, expected behavior, and observed behavior. For mapping discrepancies, include the exact source and NWB property path where available. Share a minimal reproducible example and omit private information or credentials.
