from pathlib import Path
import csv
import tempfile
import unittest

from claimstab.core import build_claim_stability, compare_claim_frameworks


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class ClaimStabilityTests(unittest.TestCase):
    def test_framework_outputs_claim_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            claims = root / "claims.csv"
            reconstruction = root / "reconstruction.csv"
            endpoints = root / "endpoints.csv"
            output = root / "output"
            write_csv(
                claims,
                [
                    "claim_id",
                    "claim_text",
                    "claim_type",
                    "reconstruction_id",
                    "manual_evidence_grade",
                    "manual_override_reason",
                    "notes",
                ],
                [
                    {
                        "claim_id": "C1",
                        "claim_text": "Treatment changes composition",
                        "claim_type": "effect",
                        "reconstruction_id": "R1",
                        "manual_evidence_grade": "",
                        "notes": "",
                    },
                    {
                        "claim_id": "C2",
                        "claim_text": "Treatment does not change diversity",
                        "claim_type": "null",
                        "reconstruction_id": "R1",
                        "manual_evidence_grade": "",
                        "notes": "",
                    },
                    {
                        "claim_id": "C3",
                        "claim_text": "A treatment has a stable rank",
                        "claim_type": "ranking",
                        "reconstruction_id": "R2",
                        "manual_evidence_grade": "",
                        "notes": "",
                    },
                    {
                        "claim_id": "C4",
                        "claim_text": "A missing analysis can be reproduced",
                        "claim_type": "not_verifiable",
                        "reconstruction_id": "R1",
                        "manual_evidence_grade": "",
                        "notes": "",
                    },
                    {
                        "claim_id": "C5",
                        "claim_text": "Composition differs by treatment",
                        "claim_type": "difference",
                        "reconstruction_id": "R1",
                        "manual_evidence_grade": "",
                        "notes": "",
                    },
                    {
                        "claim_id": "C6",
                        "claim_text": "A partially testable claim remains conditional",
                        "claim_type": "difference",
                        "reconstruction_id": "R1",
                        "manual_evidence_grade": "",
                        "manual_override_reason": "",
                        "notes": "",
                    },
                ],
            )
            write_csv(
                reconstruction,
                [
                    "reconstruction_id",
                    "domain",
                    "layer",
                    "metric",
                    "value",
                    "threshold",
                    "status",
                    "source",
                    "notes",
                ],
                [
                    {
                        "reconstruction_id": "R1",
                        "domain": "16S",
                        "layer": "phylum",
                        "metric": "mean_bray",
                        "value": "0.03",
                        "threshold": "0.10",
                        "status": "stable",
                        "source": "fixture",
                        "notes": "",
                    },
                    {
                        "reconstruction_id": "R2",
                        "domain": "ITS",
                        "layer": "phylum",
                        "metric": "mean_bray",
                        "value": "0.15",
                        "threshold": "0.10",
                        "status": "partial",
                        "source": "fixture",
                        "notes": "",
                    },
                ],
            )
            endpoint_rows = []
            for pipeline in ("A", "B", "C"):
                endpoint_rows.extend(
                    [
                        {
                            "claim_id": "C1",
                            "domain": "16S",
                            "outcome": "beta",
                            "contrast": "treatment",
                            "pipeline": pipeline,
                            "sample_set": "primary",
                            "estimate": "0.2",
                            "p_value": "0.01",
                            "direction": "positive",
                            "rank": "NA",
                            "testable": "true",
                            "source": "fixture",
                            "notes": "",
                        },
                        {
                            "claim_id": "C2",
                            "domain": "16S",
                            "outcome": "shannon",
                            "contrast": "treatment",
                            "pipeline": pipeline,
                            "sample_set": "primary",
                            "estimate": "1.2",
                            "p_value": "0.30",
                            "direction": "not_applicable",
                            "rank": "NA",
                            "testable": "true",
                            "source": "fixture",
                            "notes": "",
                        },
                        {
                            "claim_id": "C3",
                            "domain": "ITS",
                            "outcome": "reference_rank",
                            "contrast": "AEFP",
                            "pipeline": pipeline,
                            "sample_set": "primary",
                            "estimate": "0.2",
                            "p_value": "0.20",
                            "direction": "not_applicable",
                            "rank": "1" if pipeline != "C" else "2",
                            "testable": "true",
                            "source": "fixture",
                            "notes": "",
                        },
                        {
                            "claim_id": "C5",
                            "domain": "16S",
                            "outcome": "beta",
                            "contrast": "composition",
                            "pipeline": pipeline,
                            "sample_set": "primary",
                            "estimate": "0.3",
                            "p_value": "0.01",
                            "direction": "not_applicable",
                            "rank": "",
                            "testable": "true",
                            "source": "fixture",
                            "notes": "",
                        },
                        {
                            "claim_id": "C6",
                            "domain": "16S",
                            "outcome": "beta",
                            "contrast": "partial",
                            "pipeline": pipeline,
                            "sample_set": "primary",
                            "estimate": "0.2",
                            "p_value": "0.01" if pipeline != "C" else "",
                            "direction": "not_applicable",
                            "rank": "",
                            "testable": "false" if pipeline == "C" else "true",
                            "source": "fixture",
                            "notes": "one planned specification unavailable",
                        },
                    ]
                )
            write_csv(
                endpoints,
                [
                    "claim_id",
                    "domain",
                    "outcome",
                    "contrast",
                    "pipeline",
                    "sample_set",
                    "estimate",
                    "p_value",
                    "direction",
                    "rank",
                    "testable",
                    "source",
                    "notes",
                ],
                endpoint_rows
                + [
                    {
                        "claim_id": "C4",
                        "domain": "16S",
                        "outcome": "legacy_da",
                        "contrast": "not available",
                        "pipeline": "not available",
                        "sample_set": "not available",
                        "estimate": "",
                        "p_value": "",
                        "direction": "not_applicable",
                        "rank": "",
                        "testable": "false",
                        "source": "fixture",
                        "notes": "",
                    }
                ],
            )
            paths = build_claim_stability(claims, reconstruction, endpoints, output)
            with paths["claim_stability_matrix"].open(encoding="utf-8-sig") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 6)
            by_id = {row["claim_id"]: row for row in rows}
            self.assertEqual(by_id["C1"]["evidence_grade"], "strong")
            self.assertEqual(by_id["C2"]["evidence_grade"], "strong")
            self.assertEqual(by_id["C3"]["evidence_grade"], "not_supported")
            self.assertEqual(by_id["C4"]["evidence_grade"], "not_verifiable")
            self.assertEqual(by_id["C5"]["evidence_grade"], "strong")
            self.assertEqual(by_id["C6"]["evidence_grade"], "moderate")
            self.assertEqual(by_id["C6"]["specification_coverage"], "partial")
            self.assertEqual(by_id["C6"]["coverage_downgraded"], "True")
            self.assertIn("Claims: 6", paths["report"].read_text(encoding="utf-8"))

            compared = compare_claim_frameworks(
                claims, reconstruction, endpoints, output
            )
            with compared["framework_comparison"].open(
                encoding="utf-8-sig"
            ) as handle:
                comparison_rows = list(csv.DictReader(handle))
            self.assertEqual(len(comparison_rows), 6)
            self.assertIn("majority_call", comparison_rows[0])
            self.assertIn("claimstab_grade", comparison_rows[0])
            self.assertTrue(compared["framework_summary"].exists())


if __name__ == "__main__":
    unittest.main()
