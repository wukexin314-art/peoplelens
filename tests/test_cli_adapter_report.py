from __future__ import annotations

import csv
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ADAPTER = load("adapt_greenhouse")
REPORT = load("render_report")


class CliAdapterReportTest(unittest.TestCase):
    def test_greenhouse_adapter_and_funnel_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "greenhouse.csv"
            with source.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "Application ID",
                        "Candidate ID",
                        "Requisition ID",
                        "Department Name",
                        "Application Source Name",
                        "Recruiter Name",
                        "Application Stage Name",
                        "Application Stage Entered At",
                        "Application Stage Exited At",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "Application ID": "A1",
                        "Candidate ID": "C1",
                        "Requisition ID": "R1",
                        "Department Name": "Operations",
                        "Application Source Name": "Referral",
                        "Recruiter Name": "Recruiter A",
                        "Application Stage Name": "Application Review",
                        "Application Stage Entered At": "2026-01-01",
                        "Application Stage Exited At": "2026-01-02",
                    }
                )
            adapted = root / "canonical.csv"
            manifest = ADAPTER.adapt(source, adapted, {})
            with adapted.open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            report = root / "report.html"
            REPORT.render(ROOT / "examples" / "recruiting-funnel" / "output", report)
            document = report.read_text(encoding="utf-8")

        self.assertEqual(manifest["output_rows"], 1)
        self.assertEqual(row["stage"], "Application Review")
        self.assertEqual(row["source"], "Referral")
        self.assertIn("Recruiting funnel", document)
        self.assertIn("Decision snapshot", document)
        self.assertIn("Candidate journey", document)
        self.assertIn("Quality gate", document)
        self.assertIn("Protected", document)
        self.assertIn("n=6, directional", document)
        self.assertIn("Interviewed · 6.00 days", document)
        self.assertIn("Wait to start", document)
        self.assertNotIn("<script", document)

    def test_stage_outcomes_cannot_be_reconstructed_from_stage_totals(self) -> None:
        rows = [
            {"stage": "screened", "outcome": "rejected", "application_count": "7"},
            {"stage": "screened", "outcome": "candidate_withdrew", "application_count": "2"},
            {"stage": "assessed", "outcome": "rejected", "application_count": "1"},
            {"stage": "offered", "outcome": "offer_declined", "application_count": "6"},
        ]
        result = REPORT.protected_outcomes(rows, 5)

        self.assertEqual(
            [(row["stage"], row["outcome"], row["application_count"]) for row in result],
            [("screened", "detail protected", ""), ("assessed", "detail protected", ""), ("offered", "offer_declined", "6")],
        )

    def test_workforce_report_is_rich_and_privacy_aware(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "workforce-report.html"
            REPORT.render(ROOT / "examples" / "workforce" / "output", report)
            document = report.read_text(encoding="utf-8")

        self.assertIn("Workforce movement", document)
        self.assertIn("Cohort retention", document)
        self.assertIn("Breakdown protected", document)
        self.assertNotIn("23.5%", document)
        self.assertNotIn("<script", document)

    def test_unified_cli_help(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "peoplelens.py"), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("adapt-greenhouse", result.stdout)
        self.assertIn("workforce", result.stdout)


if __name__ == "__main__":
    unittest.main()
