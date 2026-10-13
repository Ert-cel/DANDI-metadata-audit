import unittest

from metadata_audit.config import AuditConfig
from metadata_audit.models import AuditResult, Evidence
from metadata_audit.output.workbook import _requirement_review, _nwb_findings
from metadata_audit.processing.mapping import matches_context, nwb_property_evidence


class PilotMappingTest(unittest.TestCase):
    def test_electrode_channel_does_not_populate_optical_channel(self):
        result = AuditResult(
            nwb_rows=[{"extraction_status": "Success"}],
            modality_classification={"detected_modalities": ["Extracellular electrophysiology"]},
            evidence=[Evidence(audit_field="channel_name", value="sig001", source_type="NWB file",
                               source_location="sub-1.nwb:electrodes/channel_name[row 0]")],
        )
        rows = _requirement_review(AuditConfig("001177"), result)
        optical = [r for r in rows if r["Field"] == "channel_name"]
        self.assertTrue(optical)
        self.assertTrue(all(not r["NWB value"] and "not assessed" in r["Match status"] for r in optical))
        self.assertFalse(matches_context("channel_name", "a.nwb:electrodes/channel_name[row 0]", "Optical channel"))

    def test_subject_property_requires_subject_path_and_deduplicates_roundtrip(self):
        props = [
            {"asset_id": "a", "asset_path": "a.nwb", "object_path": "subject",
             "property": "date_of_birth", "value": "2021-04-22 00:00:00-07:00", "evidence_kind": "NWB structured field"},
            {"asset_id": "a", "asset_path": "a.nwb", "object_path": "/general/subject/date_of_birth",
             "property": "[scalar]", "value": "2021-04-22T00:00:00-07:00", "evidence_kind": "NWB scalar dataset", "read_status": "Read"},
        ]
        evidence = nwb_property_evidence("001177", props)
        self.assertEqual(len(evidence), 1)
        self.assertIn("/general/subject/date_of_birth", evidence[0].source_location)

    def test_findings_keep_rate_and_subject_description_with_context(self):
        result = AuditResult(
            nwb_rows=[{"asset_id": "a", "asset_path": "a.nwb", "extraction_status": "Success",
                       "subject_description": "Injection details", "electrode_count": 32}],
            nwb_object_rows=[{"asset_id": "a", "object_category": "acquisition", "object_name": "ElectricalSeries0",
                              "neurodata_type": "ElectricalSeries", "rate": 30000, "unit": "volts"}],
        )
        findings = _nwb_findings(AuditConfig("001177"), result)
        self.assertTrue(any("30000 Hz" in r["Extracted value"] for r in findings))
        self.assertTrue(any(r["NWB finding"] == "Subject description" and
                            "Narrative" in r["Interpretation"] for r in findings))


if __name__ == "__main__":
    unittest.main()
