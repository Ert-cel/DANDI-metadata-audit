# Pilot check

1. Keep the former publication-based audit separate and choose a new output workbook path.
2. Run `python run_audit.py doctor`, then the three-file example in README.md.
3. Check every NWB read status in Dataset Inventory and NWB File Metadata.
4. Compare the pilot's NWB Properties paths with the same files in Neurosift.
5. In Common Data Elements, review the NWB Value and NWB Path. DANDI Reference is a separate reference column, never NWB evidence.
6. Use Source Records for the original NWB file path or DANDI metadata path; filter Evidence Role to distinguish the two sources.
7. Confirm experiment context before interpreting any blank field. Check optogenetics and behavior as additional methods when present.
8. Pin the published DANDI version and run the full batch after the pilot agrees with direct inspection.
