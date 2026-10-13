# Core audit workflow

1. Supply a Dandiset ID and optionally pin a published DANDI version.
2. The DANDI API retrieves dataset metadata, the asset inventory, and associated resources. These values are labeled **DANDI reference**.
3. PyNWB reads each selected NWB file, nested objects, scalar fields, and DynamicTable metadata cells. HDF5 inspection adds attributes, scalar datasets, and array shape/type inventories. Read errors are logged.
4. The metadata inventory goes to `NWB_Properties_<ID>.jsonl.gz`. The workbook displays the first 50,000 property records in **NWB Properties**. **Source Records** groups populated values for review and carries separately labeled DANDI references; technical details and individual repeated paths remain in NWB Properties.
5. NWB values are matched against the context-specific field catalog for modalities observed in scanned assets. **Common Data Elements** shows relevant fields; **Requirement Review** and **Allen Requirements** keep the full register. An electrode channel cannot satisfy an optical channel requirement. Narrative and derived matches require review; no match does not prove absence.
6. **NWB Findings**, **Dataset Features**, **NWB File Metadata**, **NWB Objects**, **Electrode Groups**, **Asset Inventory**, and **Dataset Inventory** summarize findings, sample rates, and inspection status.

Associated publications, CatalystNeuro pages, and usage statistics are not fetched in this run. Keep the earlier manual publication audit separate for later reconciliation. Large signals and images are inventoried by shape and type, not exported as raw samples. Long cell values are truncated and flagged.
