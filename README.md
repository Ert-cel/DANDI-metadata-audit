DANDI/NWB Metadata Audit

Author: Celine Ertekin

Python metadata-audit tools developed during my internship with the Coalition for Aligning Science (CAS), supporting the Aligning Science Across Parkinson's (ASAP) Initiative, alongside subsequent work on NWB extraction. These engines organize metadata and source evidence into Excel workbooks to support review of reporting completeness and data reuse.

Included engines
**v4.1 — Internship development engine**
Combines DANDI metadata and selected NWB fields with CatalystNeuro curated dataset records, linked-publication lookup through Crossref/PubMed/PMC, and headline DANDI usage summaries. Narrative-derived findings are candidates requiring manual review.
This supplied snapshot has not been run and requires validation. It represents internship development work rather than a verified executable that generated the completed audit findings.
[Code and usage instructions](original-DANDI_Metadata_Audit_Engine_v4.1/README.md)

**v5.0 — NWB extraction development engine**
Focuses on more detailed NWB inspection using PyNWB and native HDF5 access. It records metadata paths, read status, and array shape/type information; writes an Excel workbook and compressed property inventory; and keeps DANDI references separate from evidence that a value is present in NWB. Publication-text retrieval and usage summaries are not part of this workflow.
This is a development version requiring further live validation. Improved extraction performance has not been established.
[Code and usage instructions](dandi-nwb-metadata-audit_development_v5.0/README.md)

Getting started
Choose an engine and follow its README. Both declare Python 3.10 or newer. Run commands inside the selected engine folder and use a separate Python environment for each version because both use the same package name.
Start with a small pilot and inspect the source files before running a full audit. An unmatched or Not Reported field does not prove that information is absent across a dataset. Record the repository commit, engine version, published DANDI version, command, and installed dependencies for reproducibility.

The v4.1/v5.0 labels identify project snapshots. Internal package versions retain earlier labels because the code was preserved unchanged; see each engine's README for details.

Software and source credits
Both engines use PyNWB (NWBHDF5IO) to read NWB files, the DANDI Python client for dataset/asset discovery, remfile for remote access, h5py for HDF5 access, and openpyxl for Excel output. v4.1 also uses CatalystNeuro curated metadata and publication/usage resources. These libraries and sources are distinct from this project's audit logic.
- PyNWB documentation
- DANDI Archive
- CatalystNeuro ASAP access-analysis source
  
PyNWB citation
Following the official PyNWB citation guidance:
Rübel, O., et al. (2022). The Neurodata Without Borders ecosystem for neurophysiological data science. eLife, 11, e78362. doi:10.7554/eLife.78362.
