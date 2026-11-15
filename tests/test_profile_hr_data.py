from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("profile_hr_data", ROOT / "scripts" / "profile_hr_data.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ProfileParquetTest(unittest.TestCase):
    def test_profiles_parquet_without_exposing_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "employees.parquet"
            pq.write_table(
                pa.table(
                    {
                        "employee_id": ["E1", "E1", None],
                        "MonthlyIncome": ["1000", "2000", "3000"],
                        "hire_date": ["2026-01-01", "not-a-date", ""],
                    }
                ),
                path,
            )
            report = MODULE.profile(path, None, None, "employee_id", None)

        self.assertEqual(report["source"]["format"], "parquet")
        self.assertEqual(report["shape"], {"rows": 3, "columns": 3})
        self.assertEqual(report["id_check"]["blank_count"], 1)
        self.assertEqual(report["id_check"]["duplicate_row_count"], 1)
        self.assertEqual(report["quality_flags"]["date_parse_failures"], {"hire_date": 1})
        sensitive = {
            item["column"]: item["category"]
            for item in report["privacy_flags"]["likely_sensitive_columns"]
        }
        self.assertEqual(sensitive["MonthlyIncome"], "compensation")
        self.assertNotIn("E1", str(report))


if __name__ == "__main__":
    unittest.main()
