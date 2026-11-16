from __future__ import annotations

import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("analyze_workforce", ROOT / "scripts" / "analyze_workforce.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class WorkforceTest(unittest.TestCase):
    @staticmethod
    def read_rows(path: Path) -> list[dict[str, str]]:
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def test_workforce_metrics_and_mature_cohort(self) -> None:
        settings = MODULE.load_json_yaml(ROOT / "configs" / "workforce.example.yaml")
        settings["minimum_cell_size"] = 1
        rows = [
            ["E1", "2025-01-01", "", "", "A", "Regular", "1"],
            ["E2", "2025-01-01", "2026-02-01", "Resignation", "A", "Regular", "1"],
            ["E3", "2025-01-01", "", "", "B", "Part Time", "0.5"],
            ["E4", "2026-01-01", "2026-01-20", "Termination", "A", "Regular", "1"],
            ["E5", "2026-03-01", "", "", "B", "Regular", "1"],
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "workforce.csv"
            with source.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["employee_id", "hire_date", "separation_date", "separation_type", "business_unit", "employment_type", "fte"])
                writer.writerows(rows)
            output = root / "output"
            MODULE.analyze(source, settings, output)
            metrics = {row["metric_name"]: row for row in self.read_rows(output / "workforce_metrics.csv")}
            cohort = self.read_rows(output / "cohort_summary.csv")[0]
            separation_types = self.read_rows(output / "separation_summary.csv")
            rendered = " ".join(path.read_text(encoding="utf-8") for path in output.iterdir() if path.suffix in {".csv", ".md", ".json"})

        self.assertEqual(metrics["opening_headcount"]["value"], "3")
        self.assertEqual(metrics["closing_headcount"]["value"], "3")
        self.assertEqual(metrics["period_hires"]["value"], "2")
        self.assertEqual(metrics["period_separations"]["value"], "2")
        self.assertEqual(metrics["turnover_rate"]["value"], "0.6667")
        self.assertEqual(metrics["closing_fte"]["value"], "2.50")
        self.assertEqual(cohort["mature_hires"], "1")
        self.assertEqual(cohort["early_attrition_rate"], "1.0000")
        self.assertTrue(all(row["suppressed"] == "false" for row in separation_types))
        self.assertNotIn("E1", rendered)

    def test_invalid_input_leaves_no_outputs(self) -> None:
        settings = MODULE.load_json_yaml(ROOT / "configs" / "workforce.example.yaml")
        settings["period_end"] = "2027-01-01"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "workforce.csv"
            source.write_text(
                "employee_id,hire_date,separation_date,separation_type,business_unit,employment_type,fte\n"
                "E1,2026-01-01,,,A,Regular,1\n",
                encoding="utf-8",
            )
            output = root / "output"
            with self.assertRaisesRegex(ValueError, "period_end cannot be after"):
                MODULE.analyze(source, settings, output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
