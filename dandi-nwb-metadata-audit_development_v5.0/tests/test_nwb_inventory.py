"""Regression checks for evidence provenance and metadata error reporting."""
import gzip
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

for name in ("h5py", "remfile", "pynwb"):
    if name not in sys.modules:
        sys.modules[name] = types.ModuleType(name)
sys.modules["h5py"].Group = type("Group", (), {})
sys.modules["h5py"].Dataset = type("Dataset", (), {})
sys.modules["h5py"].Reference = type("Reference", (), {"__bool__": lambda self: True})
sys.modules["remfile"].DiskCache = lambda path: path
sys.modules["pynwb"].NWBHDF5IO = object

from metadata_audit.config import AuditConfig
from metadata_audit.extractors import nwb
from metadata_audit.models import AuditResult
from metadata_audit.output.workbook import _requirement_review, write_master_workbook


class Asset:
    def __init__(self, identifier):
        self.identifier = identifier
        self.path = identifier + ".nwb"


class InventoryTest(unittest.TestCase):
    def test_hdf5_object_reference_is_logged_as_a_path(self):
        class Group(sys.modules["h5py"].Group):
            def __init__(self, attrs=None, name=""):
                self.attrs = attrs or {}
                self.name = name
            def visititems(self, visit):
                visit("acquisition/series/electrodes", Group({"table": reference}))
            def __getitem__(self, key):
                return Group(name="/general/extracellular_ephys/electrodes")
        reference = sys.modules["h5py"].Reference()
        nwb = type("NWB", (), {"all_children": lambda self: []})()
        rows = __import__("metadata_audit.extractors.nwb", fromlist=["_deep_rows"])._deep_rows(
            nwb, Group(), "001177", "asset", "a.nwb")
        target = next(r for r in rows if r.get("property") == "@table")
        self.assertEqual(target["value"], "/general/extracellular_ephys/electrodes")
        self.assertEqual(target["read_status"], "Read")

    def test_repeated_values_keep_both_file_paths_and_all_objects(self):
        def extracted(asset, cache, did):
            prop = {"dandiset_id": did, "asset_id": asset.identifier,
                    "asset_path": asset.path, "object_path": "/general/subject",
                    "property": "sex", "value": "F", "evidence_kind": "NWB structured field"}
            obj = {"asset_id": asset.identifier, "asset_path": asset.path,
                   "object_category": "nested", "object_name": "subject", "neurodata_type": "Subject"}
            return ({"extraction_status": "Success", "asset_id": asset.identifier}, [obj], [], [prop])

        with tempfile.TemporaryDirectory() as tmp:
            config = AuditConfig("001177", output_directory=Path(tmp), cache_directory=Path(tmp) / "cache")
            with patch.object(nwb, "_extract_one", side_effect=extracted):
                rows, objects, _, preview, matches = nwb.extract_nwb_assets(config, [Asset("a"), Asset("b")])
            self.assertEqual(len(rows), 2)
            self.assertEqual(len(objects), 2)
            self.assertEqual(len(matches), 2)
            self.assertEqual({r["asset_id"] for r in matches}, {"a", "b"})
            with gzip.open(Path(tmp) / "NWB_Properties_001177.jsonl.gz", "rt") as handle:
                self.assertEqual(len([json.loads(line) for line in handle]), 2)

    def test_property_errors_prevent_absence_claim(self):
        result = AuditResult(nwb_rows=[{"extraction_status": "Success", "metadata_read_errors": 1}],
                             modality_classification={"detected_modalities": []})
        rows = _requirement_review(AuditConfig("001177"), result)
        self.assertTrue(all("inspection incomplete" in r["Match status"] or
                            "mapping required" in r["Match status"] or
                            "not assessed" in r["Match status"] for r in rows))

    def test_source_log_includes_unmapped_properties(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            config = AuditConfig("001177", master_workbook=Path(tmp) / "result.xlsx",
                                 output_directory=Path(tmp),
                                 template_path=root / "templates/Metadata_Audit_Master_Template.xlsx")
            result = AuditResult(nwb_rows=[{"extraction_status": "Success"}],
                                 nwb_property_rows=[{"asset_id": "a", "asset_path": "a.nwb",
                                                     "object_path": "/general/subject", "property": "custom_field",
                                                     "value": "custom value", "evidence_kind": "NWB table cell"}],
                                 modality_classification={"detected_modalities": []})
            from openpyxl import load_workbook
            wb = load_workbook(write_master_workbook(config, result), read_only=True)
            values = list(wb["Source Records"].values)
            self.assertIn("custom_field", values[1])
            self.assertIn("NWB evidence", values[1])


if __name__ == "__main__":
    unittest.main()
