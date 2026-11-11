from __future__ import annotations

import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "analyze_recruiting_funnel", ROOT / "scripts" / "analyze_recruiting_funnel.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RecruitingFunnelTest(unittest.TestCase):
    def test_synthetic_example(self) -> None:
        settings = MODULE.merge_settings(
            MODULE.load_json_yaml(ROOT / "configs" / "recruiting-funnel.example.yaml"),
            MODULE.load_json_yaml(ROOT / "configs" / "mappings" / "canonical-event-history.yaml"),
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            manifest = MODULE.analyze(
                ROOT / "examples" / "recruiting-funnel" / "applications.csv",
                settings,
                output,
            )
            self.assertEqual(manifest["distinct_applications"], 12)

            with (output / "funnel_summary.csv").open(newline="", encoding="utf-8") as handle:
                funnel = {row["stage"]: row for row in csv.DictReader(handle)}
            self.assertEqual(funnel["applied"]["reached_applications"], "12")
            self.assertEqual(funnel["started"]["reached_applications"], "4")
            self.assertEqual(funnel["offered"]["adjacent_conversion_rate"], "0.6667")

            with (output / "data_quality.csv").open(newline="", encoding="utf-8") as handle:
                quality = list(csv.DictReader(handle))
            self.assertFalse(any(int(row["count"]) for row in quality if row["severity"] == "error"))


if __name__ == "__main__":
    unittest.main()
