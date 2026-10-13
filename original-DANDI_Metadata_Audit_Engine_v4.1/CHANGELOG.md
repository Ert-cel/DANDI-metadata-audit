# Changelog

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
