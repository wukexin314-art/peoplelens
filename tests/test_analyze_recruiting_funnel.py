from __future__ import annotations

import csv
import importlib.util
import tempfile
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "analyze_recruiting_funnel", ROOT / "scripts" / "analyze_recruiting_funnel.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RecruitingFunnelTest(unittest.TestCase):
    def settings(self) -> dict:
        return MODULE.merge_settings(
            MODULE.load_json_yaml(ROOT / "configs" / "recruiting-funnel.example.yaml"),
            MODULE.load_json_yaml(
                ROOT / "configs" / "mappings" / "canonical-event-history.yaml"
            ),
        )

    def run_rows(self, rows: list[dict[str, str]], settings: dict) -> tuple[dict, Path]:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        input_path = root / "input.csv"
        fieldnames = [
            "application_id",
            "stage",
            "stage_entered_at",
            "stage_exited_at",
            "stage_outcome",
            "business_unit",
            "source",
        ]
        with input_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        output = root / "output"
        return MODULE.analyze(input_path, settings, output), output

    @staticmethod
    def read_rows(path: Path) -> list[dict[str, str]]:
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def test_synthetic_example(self) -> None:
        settings = self.settings()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            manifest = MODULE.analyze(
                ROOT / "examples" / "recruiting-funnel" / "applications.csv",
                settings,
                output,
            )
            self.assertEqual(manifest["distinct_applications"], 12)
            self.assertEqual(manifest["mature_cohort_applications"], 12)

            funnel = {
                row["stage"]: row
                for row in self.read_rows(output / "funnel_summary.csv")
            }
            self.assertEqual(funnel["applied"]["reached_applications"], "12")
            self.assertEqual(funnel["started"]["reached_applications"], "4")
            self.assertEqual(funnel["offered"]["adjacent_conversion_rate"], "0.6667")

            quality = self.read_rows(output / "data_quality.csv")
            self.assertFalse(
                any(int(row["count"]) for row in quality if row["severity"] == "error")
            )
            segments = self.read_rows(output / "segment_summary.csv")
            self.assertTrue(all(row["suppressed"] == "true" for row in segments))
            self.assertTrue(all(row["application_count"] == "" for row in segments))
            for name, detail in (("stage_outcomes.csv", "outcome"), ("backlog_aging.csv", "age_band")):
                rows = self.read_rows(output / name)
                self.assertTrue(rows)
                self.assertTrue(all(row[detail] == "detail protected" and row["application_count"] == "" for row in rows))

    def test_stage_detail_suppression_hides_whole_stage(self) -> None:
        rows = [
            {"stage": "screened", "outcome": "rejected", "application_count": 7},
            {"stage": "screened", "outcome": "candidate_withdrew", "application_count": 2},
            {"stage": "offered", "outcome": "offer_declined", "application_count": 6},
        ]
        result = MODULE.protect_stage_detail(rows, "outcome", 5)
        self.assertEqual(
            [(row["stage"], row["outcome"], row["application_count"], row["suppressed"]) for row in result],
            [("screened", "detail protected", "", "true"), ("offered", "offer_declined", 6, "false")],
        )

    def test_conversion_uses_same_applications_and_reports_mapping_gaps(self) -> None:
        settings = self.settings()
        settings["cohort"] = {"minimum_followup_days": 0}
        rows = [
            {"application_id": "A1", "stage": "Applied", "stage_entered_at": "2026-01-01", "stage_exited_at": "2026-01-02"},
            {"application_id": "A1", "stage": "Screened", "stage_entered_at": "2026-01-02"},
            {"application_id": "A2", "stage": "Applied", "stage_entered_at": "2026-01-03"},
            {"application_id": "B1", "stage": "Screened", "stage_entered_at": "2026-01-04"},
            {"application_id": "U1", "stage": "Phone Screen", "stage_entered_at": "2026-01-05"},
            {"application_id": "F1", "stage": "Applied", "stage_entered_at": "2026-04-01"},
        ]
        _, output = self.run_rows(rows, settings)

        funnel = {
            row["stage"]: row
            for row in self.read_rows(output / "funnel_summary.csv")
        }
        self.assertEqual(funnel["applied"]["reached_applications"], "2")
        self.assertEqual(funnel["applied"]["adjacent_conversion_rate"], "0.5000")
        quality = {
            row["check"]: int(row["count"])
            for row in self.read_rows(output / "data_quality.csv")
        }
        self.assertEqual(quality["missing_first_stage"], 1)
        self.assertEqual(quality["unknown_stage"], 1)
        self.assertEqual(quality["future_stage_entered_at"], 1)
        mappings = self.read_rows(output / "mapping_report.csv")
        phone_screen = next(
            row for row in mappings if row["source_value"] == "Phone Screen"
        )
        self.assertEqual(phone_screen["status"], "unmapped")
        self.assertEqual(phone_screen["event_count"], "1")

    def test_timezone_duration_and_exited_stage_is_not_backlog(self) -> None:
        settings = self.settings()
        settings["as_of_date"] = "2026-01-31"
        settings["cohort"] = {"minimum_followup_days": 0}
        rows = [
            {
                "application_id": "A1",
                "stage": "Applied",
                "stage_entered_at": "2026-01-01T23:00:00-05:00",
                "stage_exited_at": "2026-01-02T05:00:00Z",
            }
        ]
        _, output = self.run_rows(rows, settings)
        funnel = {
            row["stage"]: row
            for row in self.read_rows(output / "funnel_summary.csv")
        }
        self.assertEqual(funnel["applied"]["median_time_in_stage_days"], "0.04")
        self.assertEqual(funnel["applied"]["active_backlog"], "0")
        quality = {
            row["check"]: int(row["count"])
            for row in self.read_rows(output / "data_quality.csv")
        }
        self.assertEqual(quality["exited_without_next_stage"], 1)
        self.assertIsNone(MODULE.parse_datetime("03/04/2026"))

    def test_future_exit_is_open_at_as_of_date(self) -> None:
        settings = self.settings()
        settings["cohort"] = {"minimum_followup_days": 0}
        rows = [
            {
                "application_id": "A1",
                "stage": "Applied",
                "stage_entered_at": "2026-01-01",
                "stage_exited_at": "2026-04-01",
                "stage_outcome": "rejected",
            }
        ]
        _, output = self.run_rows(rows, settings)
        funnel = {
            row["stage"]: row
            for row in self.read_rows(output / "funnel_summary.csv")
        }
        self.assertEqual(funnel["applied"]["active_backlog"], "1")
        self.assertEqual(funnel["applied"]["terminal_drop_offs"], "0")
        quality = {
            row["check"]: int(row["count"])
            for row in self.read_rows(output / "data_quality.csv")
        }
        self.assertEqual(quality["stage_exit_after_as_of"], 1)

    def test_small_cell_uses_complementary_suppression(self) -> None:
        settings = self.settings()
        settings["cohort"] = {"minimum_followup_days": 0}
        settings["segments"] = ["source"]
        rows = []
        for index, source in enumerate(["Large A"] * 5 + ["Large B"] * 5 + ["Small"]):
            rows.append(
                {
                    "application_id": f"A{index}",
                    "stage": "Applied",
                    "stage_entered_at": "2026-01-01",
                    "source": source,
                }
            )
        _, output = self.run_rows(rows, settings)
        segments = self.read_rows(output / "segment_summary.csv")
        suppressed = [row for row in segments if row["suppressed"] == "true"]
        self.assertEqual(len(suppressed), 2)
        self.assertEqual(
            {row["suppression_reason"] for row in suppressed},
            {"small_cell", "complementary"},
        )

    def test_cohort_window_and_maturity(self) -> None:
        settings = self.settings()
        settings["cohort"] = {
            "start_date": "2026-01-01",
            "end_date": "2026-03-31",
            "minimum_followup_days": 30,
        }
        rows = [
            {"application_id": "A1", "stage": "Applied", "stage_entered_at": "2026-01-01", "stage_exited_at": "2026-01-10"},
            {"application_id": "A1", "stage": "Started", "stage_entered_at": "2026-01-10"},
            {"application_id": "A2", "stage": "Applied", "stage_entered_at": "2026-03-20", "stage_exited_at": "2026-03-25"},
            {"application_id": "A2", "stage": "Started", "stage_entered_at": "2026-03-25"},
        ]
        manifest, output = self.run_rows(rows, settings)
        self.assertEqual(manifest["eligible_cohort_applications"], 2)
        self.assertEqual(manifest["mature_cohort_applications"], 1)
        cohort = self.read_rows(output / "cohort_summary.csv")[0]
        self.assertEqual(cohort["immature_applications"], "1")
        funnel = {
            row["stage"]: row
            for row in self.read_rows(output / "funnel_summary.csv")
        }
        self.assertEqual(funnel["applied"]["reached_applications"], "1")
        self.assertEqual(funnel["started"]["reached_applications"], "1")

    def test_invalid_metric_config_writes_no_partial_outputs(self) -> None:
        settings = self.settings()
        settings["metrics"] = [{"name": "bad", "type": "not_supported"}]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            with self.assertRaisesRegex(ValueError, "Unsupported configured metric type"):
                MODULE.analyze(
                    ROOT / "examples" / "recruiting-funnel" / "applications.csv",
                    settings,
                    output,
                )
            self.assertFalse(output.exists())

    def test_failed_forced_run_preserves_previous_outputs(self) -> None:
        settings = self.settings()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            output.mkdir()
            previous = output / "funnel_summary.csv"
            previous.write_text("previous successful run\n", encoding="utf-8")
            original_write = MODULE.write_csv
            calls = 0

            def fail_after_first_file(*args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated write failure")
                return original_write(*args, **kwargs)

            with mock.patch.object(MODULE, "write_csv", side_effect=fail_after_first_file):
                with self.assertRaisesRegex(OSError, "simulated write failure"):
                    MODULE.analyze(
                        ROOT / "examples" / "recruiting-funnel" / "applications.csv",
                        settings,
                        output,
                        force=True,
                    )
            self.assertEqual(previous.read_text(encoding="utf-8"), "previous successful run\n")
            self.assertEqual([path.name for path in output.iterdir()], ["funnel_summary.csv"])

    def test_segment_attribution_defaults_to_entry_stage(self) -> None:
        settings = self.settings()
        settings["cohort"] = {"minimum_followup_days": 0}
        settings["segments"] = ["source"]
        settings["minimum_cell_size"] = 1
        rows = [
            {"application_id": "A1", "stage": "Applied", "stage_entered_at": "2026-01-01", "source": "Referral"},
            {"application_id": "A1", "stage": "Started", "stage_entered_at": "2026-01-10", "source": "Corrected Source"},
        ]
        _, output = self.run_rows(rows, settings)
        segments = self.read_rows(output / "segment_summary.csv")
        self.assertEqual(segments[0]["value"], "Referral")
        quality = {row["check"]: int(row["count"]) for row in self.read_rows(output / "data_quality.csv")}
        self.assertEqual(quality["segment_value_changes"], 1)


if __name__ == "__main__":
    unittest.main()
