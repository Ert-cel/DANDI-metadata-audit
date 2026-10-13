# Start Here — v4.1

This is the internship development snapshot identified by the author as v4.1. The supplied version has not been run; outputs and extraction behavior need validation. Internal Python/package labels are preserved. See README.md for the version explanation and full instructions.

1. Open a terminal in this folder, containing `run_audit.py` and `templates/`.
2. Create a compatible Python environment and install `.[dev]` as shown in README.md.
3. Run `doctor` to check the local setup.
4. Use a fresh workbook and a small pilot, such as Dandiset 001177 with `--max-assets 3`.
5. Check file failures, source evidence, curated/detected modalities, publication candidates, and software/probe/anaesthesia mappings directly.
6. Pin an actual published DANDI version before reproducible analysis.
7. Attempt a full run only after pilot validation.

Example Windows pilot after installation:

```powershell
.\.venv\Scripts\python.exe run_audit.py audit 001177 --max-assets 3 --master-workbook outputs/pilot/Review.xlsx
```

Do not interpret a workbook `Complete` label or an unmatched field as proof of complete inspection. Preserve any earlier internship analysis separately.
