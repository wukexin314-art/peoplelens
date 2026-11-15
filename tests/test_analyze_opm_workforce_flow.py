from __future__ import annotations

import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "analyze_opm_workforce_flow", ROOT / "scripts" / "analyze_opm_workforce_flow.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class OpmWorkforceFlowTest(unittest.TestCase):
    @staticmethod
    def read_rows(path: Path) -> list[dict[str, str]]:
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def test_effective_month_filter_and_small_cell_suppression(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            accessions = root / "accessions.parquet"
            separations = root / "separations.parquet"
            pq.write_table(
                pa.table(
                    {
                        "count": ["4", "6", "3"],
                        "personnel_action_effective_date_yyyymm": ["202608", "202608", "202607"],
                        "accession_category": ["NEW HIRE", "TRANSFER IN", "NEW HIRE"],
                        "department": ["Department A", "Department B", "Department A"],
                    }
                ),
                accessions,
            )
            pq.write_table(
                pa.table(
                    {
                        "count": ["6"],
                        "personnel_action_effective_date_yyyymm": ["202608"],
                        "separation_category": ["QUIT"],
                        "department": ["Department B"],
                    }
                ),
                separations,
            )
            output = root / "output"
            manifest = MODULE.analyze(
                accessions,
                separations,
                output,
                start_month="2026-08",
                end_month="2026-08",
            )

            monthly = self.read_rows(output / "monthly_flow.csv")
            segments = self.read_rows(output / "segment_summary.csv")
            quality = {row["check"]: int(row["count"]) for row in self.read_rows(output / "data_quality.csv")}

        self.assertEqual(manifest["accessions"], 10)
        self.assertEqual(manifest["separations"], 6)
        self.assertEqual(manifest["net_action_flow"], 4)
        self.assertEqual(monthly[0]["effective_month"], "2026-08")
        self.assertEqual(monthly[0]["net_action_flow"], "4")
        self.assertEqual(quality["outside_period"], 1)
        self.assertTrue(all(row["suppressed"] == "true" for row in segments))
        self.assertEqual(
            {row["suppression_reason"] for row in segments},
            {"small_cell", "complementary"},
        )


if __name__ == "__main__":
    unittest.main()
