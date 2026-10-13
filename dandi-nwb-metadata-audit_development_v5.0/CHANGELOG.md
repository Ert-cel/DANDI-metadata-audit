# Changelog

## 2.0.0 — Pilot review and modality-aware mapping

- Review the actual 001177 one-file pilot and distinguish the 56 NWB assets from the single scanned file.
- Add a concise NWB Findings view and group repeated source records while retaining technical details in NWB Properties and JSONL.
- Resolve common HDF5 object references instead of counting them as extraction errors.
- Gate requirement matches by observed modality and object path, including protection against matching electrode channels to optical-channel requirements.
- Keep the complete Allen register while focusing Common Data Elements on methods observed in scanned files.
- Preserve subject descriptions as NWB narrative for review and expose acquisition-type and modality candidates with explicit review status.

## 1.9.0 — NWB provenance and workflow correction

- Replace the obsolete publication and CatalystNeuro core workflow description with the actual DANDI/NWB pipeline.
- Keep the DANDI API client open while resolving remote NWB asset URLs.
- Preserve repeated evidence across assets and all NWB object rows; expose object, electrode group, and asset inventories.
- Include unmapped properties in Source Records and flag metadata read errors and truncated values.
- Keep the full requirement register visible when a modality is not detected; add a matching Core Workflow tab to both templates.
- Add regression checks for file provenance, source logging, and incomplete inspection status.

## 1.5.0 — Ephys validation build

- Split equipment into acquisition equipment, acquisition software, analysis software,
  electrode/probe, stimulation equipment, and manufacturer.
- Prevent generic NWB software descriptions from populating `probe_model`.
- Added Clampex/pCLAMP/Clampfit/Plexon Offline Sorter recognition.
- Added context-aware anaesthesia handling for terminal/perfusion versus surgical use.
- Preserve publication subsection titles in evidence source locations.
- Added Ephys Subtype to Dataset Inventory.
- Expanded Dataset Features with source, confidence, and review columns per feature.
- Added tests for the main mapping errors discovered in the 001177/001538/001777 pilot.
