# GitHub packaging notes

The supplied `DANDI_NWB_Audit_Engine_v5.0.zip` was repackaged under the repository folder `dandi-nwb-metadata-audit`.

## Changes

- Renamed the outer folder from `DANDI_Metadata_Audit_Engine` to `dandi-nwb-metadata-audit`.
- Replaced the root README with installation, usage, output interpretation, validation limits, version identity, and GitHub upload instructions.
- Added this packaging note and expanded `.gitignore` to exclude runtime artifacts.
- Preserved the historical changelog and other workflow documents.

## Preserved files

Every Python file, `pyproject.toml`, `requirements.txt`, the JSON field catalog, and both Excel templates are unchanged. Internal package names, script names, and template filenames are retained because they are referenced by the existing engine. No logic, dependencies, or internal version constants were modified.

Only the newer supplied snapshot is included. The earlier engine used for the completed audit has not been provided.

## Verification

Packaging verification compares every preserved file against the original extracted upload using SHA-256 hashes and validates the ZIP structure. Python source syntax and command-line help are checked without a live audit. No extraction-performance improvement is claimed.
