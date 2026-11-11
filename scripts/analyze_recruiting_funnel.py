#!/usr/bin/env python3
"""Analyze ATS stage-event history and produce auditable funnel outputs.

The configuration files use JSON-compatible YAML, so the script needs only the
Python standard library. Input and outputs contain aggregate recruiting data;
the script never prints candidate-level rows.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


OUTPUT_FILES = (
    "funnel_summary.csv",
    "stage_outcomes.csv",
    "backlog_aging.csv",
    "segment_summary.csv",
    "configured_metrics.csv",
    "metric_dictionary.csv",
    "data_quality.csv",
    "analysis_summary.md",
    "run_manifest.json",
)


def load_json_yaml(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path} must use JSON-compatible YAML: {exc.msg} at line {exc.lineno}"
        ) from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object at the top level")
    return value


def merge_settings(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_settings(merged[key], value)
        else:
            merged[key] = value
    return merged


def parse_datetime(value: str) -> dt.datetime | None:
    text = value.strip()
    if not text:
        return None
    try:
        parsed = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return dt.datetime.strptime(text, fmt)
        except ValueError:
            pass
    return None


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def format_number(value: float | int | None, digits: int = 4) -> str:
    if value is None:
        return ""
    if isinstance(value, int):
        return str(value)
    return f"{value:.{digits}f}"


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("The input CSV has no header row")
        headers = [header.strip() for header in reader.fieldnames]
        rows = []
        for raw in reader:
            row = {(key or "").strip(): (value or "").strip() for key, value in raw.items()}
            if any(row.values()):
                rows.append(row)
        return headers, rows


def validate_settings(settings: dict[str, Any], headers: list[str]) -> None:
    required = {"application_id", "stage", "stage_entered_at"}
    columns = settings.get("columns")
    if not isinstance(columns, dict):
        raise ValueError("Configuration requires a columns object")
    missing_mappings = sorted(required - columns.keys())
    if missing_mappings:
        raise ValueError(f"Missing required column mappings: {', '.join(missing_mappings)}")
    missing_headers = sorted(
        source for source in columns.values() if source and source not in headers
    )
    if missing_headers:
        raise ValueError(f"Mapped input columns not found: {', '.join(missing_headers)}")
    stage_order = settings.get("stage_order")
    if not isinstance(stage_order, list) or len(stage_order) < 2:
        raise ValueError("Configuration requires at least two stages in stage_order")
    if len(stage_order) != len(set(stage_order)):
        raise ValueError("stage_order contains duplicate stages")
    if not isinstance(settings.get("stage_mapping"), dict):
        raise ValueError("Configuration requires a stage_mapping object")


def band_label(age: int, cutoffs: list[int]) -> str:
    previous = 0
    for cutoff in cutoffs:
        if age <= cutoff:
            return f"{previous}-{cutoff} days"
        previous = cutoff + 1
    return f"{previous}+ days"


def quality_row(severity: str, check: str, count: int, detail: str) -> dict[str, Any]:
    return {"severity": severity, "check": check, "count": count, "detail": detail}


def analyze(
    input_path: Path,
    settings: dict[str, Any],
    output_dir: Path,
    force: bool = False,
) -> dict[str, Any]:
    headers, source_rows = read_rows(input_path)
    validate_settings(settings, headers)
    output_dir.mkdir(parents=True, exist_ok=True)
    existing = [name for name in OUTPUT_FILES if (output_dir / name).exists()]
    if existing and not force:
        raise FileExistsError(
            f"Output files already exist: {', '.join(existing)}. Use --force to replace them."
        )

    columns: dict[str, str] = settings["columns"]
    stage_order: list[str] = settings["stage_order"]
    stage_index = {stage: index for index, stage in enumerate(stage_order)}
    raw_stage_mapping = settings["stage_mapping"]
    stage_mapping = {str(key).strip().casefold(): value for key, value in raw_stage_mapping.items()}
    terminal_outcomes = {str(value).strip().casefold() for value in settings.get("terminal_outcomes", [])}
    started_stage = settings.get("started_stage", stage_order[-1])
    as_of = parse_datetime(str(settings.get("as_of_date", "")))
    if as_of is None:
        raise ValueError("Configuration requires a valid as_of_date")
    aging_bands = sorted({int(value) for value in settings.get("aging_bands_days", [7, 14, 30])})
    if any(value < 0 for value in aging_bands):
        raise ValueError("aging_bands_days cannot contain negative values")

    def cell(row: dict[str, str], canonical: str) -> str:
        source = columns.get(canonical, "")
        return row.get(source, "") if source else ""

    issues: Counter[str] = Counter()
    applications: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_rows: Counter[tuple[str, ...]] = Counter()
    valid_event_rows = 0

    for row in source_rows:
        application_id = cell(row, "application_id")
        raw_stage = cell(row, "stage")
        entered_text = cell(row, "stage_entered_at")
        exited_text = cell(row, "stage_exited_at")
        if not application_id:
            issues["missing_application_id"] += 1
            continue
        if not raw_stage:
            issues["blank_stage"] += 1
            continue
        stage = stage_mapping.get(raw_stage.casefold())
        if stage not in stage_index:
            issues["unknown_stage"] += 1
            continue
        entered = parse_datetime(entered_text)
        exited = parse_datetime(exited_text) if exited_text else None
        if entered is None:
            issues["invalid_stage_entered_at"] += 1
            continue
        if exited_text and exited is None:
            issues["invalid_stage_exited_at"] += 1
        if exited and exited < entered:
            issues["exit_before_entry"] += 1
            exited = None
        signature = (application_id, stage, entered_text, exited_text, cell(row, "stage_outcome"))
        seen_rows[signature] += 1
        event = {
            "application_id": application_id,
            "stage": stage,
            "stage_index": stage_index[stage],
            "entered": entered,
            "exited": exited,
            "outcome": cell(row, "stage_outcome").casefold(),
            "segments": {
                segment: cell(row, segment) or "Unknown"
                for segment in settings.get("segments", [])
            },
        }
        applications[application_id].append(event)
        valid_event_rows += 1

    issues["duplicate_event_rows"] = sum(count - 1 for count in seen_rows.values() if count > 1)
    reached: dict[str, set[str]] = {stage: set() for stage in stage_order}
    durations: dict[str, list[float]] = {stage: [] for stage in stage_order}
    stage_outcomes: Counter[tuple[str, str]] = Counter()
    backlog: Counter[str] = Counter()
    backlog_aging: Counter[tuple[str, str]] = Counter()
    application_segments: dict[str, dict[str, str]] = {}

    for application_id, events in applications.items():
        events.sort(key=lambda event: (event["entered"], event["stage_index"]))
        unique_events = []
        seen_signatures: set[tuple[Any, ...]] = set()
        for event in events:
            signature = (event["stage"], event["entered"], event["exited"], event["outcome"])
            if signature not in seen_signatures:
                unique_events.append(event)
                seen_signatures.add(signature)
        events = unique_events
        applications[application_id] = events
        application_segments[application_id] = events[-1]["segments"]
        previous_index = None
        for event in events:
            reached[event["stage"]].add(application_id)
            if event["exited"]:
                durations[event["stage"]].append(
                    (event["exited"] - event["entered"]).total_seconds() / 86400
                )
            if previous_index is not None:
                if event["stage_index"] < previous_index:
                    issues["stage_regressions"] += 1
                elif event["stage_index"] - previous_index > 1:
                    issues["skipped_stage_transitions"] += 1
            previous_index = event["stage_index"]

        terminal_events = [event for event in events if event["outcome"] in terminal_outcomes]
        latest = events[-1]
        if latest["outcome"] in terminal_outcomes:
            stage_outcomes[(latest["stage"], latest["outcome"])] += 1
        elif application_id not in reached.get(started_stage, set()):
            backlog[latest["stage"]] += 1
            age = max(0, (as_of - latest["entered"]).days)
            backlog_aging[(latest["stage"], band_label(age, aging_bands))] += 1
        if len({event["outcome"] for event in terminal_events}) > 1:
            issues["multiple_terminal_outcomes"] += 1

    first_stage_count = len(reached[stage_order[0]])
    funnel_rows = []
    for index, stage in enumerate(stage_order):
        current_count = len(reached[stage])
        next_count = len(reached[stage_order[index + 1]]) if index + 1 < len(stage_order) else None
        adjacent = next_count / current_count if next_count is not None and current_count else None
        cumulative = current_count / first_stage_count if first_stage_count else None
        drop_offs = sum(count for (outcome_stage, _), count in stage_outcomes.items() if outcome_stage == stage)
        funnel_rows.append(
            {
                "stage": stage,
                "reached_applications": current_count,
                "adjacent_conversion_rate": format_number(adjacent),
                "cumulative_yield_rate": format_number(cumulative),
                "terminal_drop_offs": drop_offs,
                "active_backlog": backlog[stage],
                "median_time_in_stage_days": format_number(percentile(durations[stage], 0.5), 2),
                "p75_time_in_stage_days": format_number(percentile(durations[stage], 0.75), 2),
            }
        )
    write_csv(
        output_dir / "funnel_summary.csv",
        list(funnel_rows[0]),
        funnel_rows,
    )

    outcome_rows = [
        {"stage": stage, "outcome": outcome, "application_count": count}
        for (stage, outcome), count in sorted(
            stage_outcomes.items(), key=lambda item: (stage_index[item[0][0]], item[0][1])
        )
    ]
    write_csv(output_dir / "stage_outcomes.csv", ["stage", "outcome", "application_count"], outcome_rows)

    band_order = [band_label(0 if index == 0 else aging_bands[index - 1] + 1, aging_bands) for index in range(len(aging_bands) + 1)]
    backlog_rows = [
        {"stage": stage, "age_band": band, "application_count": backlog_aging.get((stage, band), 0)}
        for stage in stage_order
        for band in band_order
        if backlog_aging.get((stage, band), 0)
    ]
    write_csv(output_dir / "backlog_aging.csv", ["stage", "age_band", "application_count"], backlog_rows)

    segment_rows = []
    for segment in settings.get("segments", []):
        values: dict[str, set[str]] = defaultdict(set)
        started: dict[str, set[str]] = defaultdict(set)
        for application_id, segment_values in application_segments.items():
            value = segment_values.get(segment, "Unknown")
            values[value].add(application_id)
            if application_id in reached.get(started_stage, set()):
                started[value].add(application_id)
        for value in sorted(values):
            denominator = len(values[value])
            numerator = len(started[value])
            segment_rows.append(
                {
                    "segment": segment,
                    "value": value,
                    "application_count": denominator,
                    "started_count": numerator,
                    "application_to_start_rate": format_number(numerator / denominator if denominator else None),
                }
            )
    write_csv(
        output_dir / "segment_summary.csv",
        ["segment", "value", "application_count", "started_count", "application_to_start_rate"],
        segment_rows,
    )

    metric_rows = []
    metric_dictionary_rows = []
    for metric in settings.get("metrics", []):
        if metric.get("type") != "stage_yield":
            # shortcut: first release executes stage-yield metrics only; add types when a real use case needs them.
            raise ValueError(f"Unsupported configured metric type: {metric.get('type')!r}")
        numerator_stage = metric.get("numerator_stage")
        denominator_stage = metric.get("denominator_stage")
        if numerator_stage not in reached or denominator_stage not in reached:
            raise ValueError(f"Metric {metric.get('name')!r} references an unknown stage")
        numerator = len(reached[numerator_stage])
        denominator = len(reached[denominator_stage])
        metric_rows.append(
            {
                "metric_name": metric["name"],
                "value": format_number(numerator / denominator if denominator else None),
                "numerator": numerator,
                "denominator": denominator,
                "as_of_date": as_of.date().isoformat(),
            }
        )
        metric_dictionary_rows.append(
            {
                "metric_name": metric["name"],
                "metric_type": "stage_yield",
                "population": f"Applications reaching {denominator_stage}",
                "numerator": f"Distinct applications reaching {numerator_stage}",
                "denominator": f"Distinct applications reaching {denominator_stage}",
                "desired_direction": metric.get("desired_direction", "contextual"),
                "known_limitations": "Requires complete stage history and a mature observation window.",
            }
        )
    write_csv(
        output_dir / "configured_metrics.csv",
        ["metric_name", "value", "numerator", "denominator", "as_of_date"],
        metric_rows,
    )
    write_csv(
        output_dir / "metric_dictionary.csv",
        [
            "metric_name",
            "metric_type",
            "population",
            "numerator",
            "denominator",
            "desired_direction",
            "known_limitations",
        ],
        metric_dictionary_rows,
    )

    quality_rows = [
        quality_row("error", "missing_application_id", issues["missing_application_id"], "Rows excluded because the application key is blank."),
        quality_row("error", "invalid_stage_entered_at", issues["invalid_stage_entered_at"], "Rows excluded because the stage entry timestamp is invalid."),
        quality_row("error", "exit_before_entry", issues["exit_before_entry"], "Stage exit precedes entry; duration was not calculated."),
        quality_row("warning", "blank_stage", issues["blank_stage"], "Rows excluded because the raw stage is blank."),
        quality_row("warning", "unknown_stage", issues["unknown_stage"], "Rows excluded because the raw stage is not mapped."),
        quality_row("warning", "invalid_stage_exited_at", issues["invalid_stage_exited_at"], "Duration was not calculated for invalid exit timestamps."),
        quality_row("warning", "duplicate_event_rows", issues["duplicate_event_rows"], "Exact duplicate stage events were counted once."),
        quality_row("warning", "stage_regressions", issues["stage_regressions"], "Applications moved to an earlier canonical stage."),
        quality_row("info", "skipped_stage_transitions", issues["skipped_stage_transitions"], "Applications skipped at least one canonical stage."),
        quality_row("warning", "multiple_terminal_outcomes", issues["multiple_terminal_outcomes"], "Applications contain conflicting terminal outcomes."),
    ]
    write_csv(output_dir / "data_quality.csv", ["severity", "check", "count", "detail"], quality_rows)

    adjacent_candidates = [
        (row["stage"], float(row["adjacent_conversion_rate"]))
        for row in funnel_rows[:-1]
        if row["adjacent_conversion_rate"]
    ]
    bottleneck = min(adjacent_candidates, key=lambda item: item[1]) if adjacent_candidates else None
    error_count = sum(row["count"] for row in quality_rows if row["severity"] == "error")
    warning_count = sum(row["count"] for row in quality_rows if row["severity"] == "warning")
    summary_lines = [
        "# Recruiting funnel summary",
        "",
        f"- As-of date: {as_of.date().isoformat()}",
        f"- Source rows: {len(source_rows)}",
        f"- Distinct applications analyzed: {len(applications)}",
        f"- Applications reaching {started_stage}: {len(reached.get(started_stage, set()))}",
        f"- Active backlog: {sum(backlog.values())}",
        f"- Terminal outcomes: {sum(stage_outcomes.values())}",
        f"- Data-quality errors: {error_count}; warnings: {warning_count}",
    ]
    if bottleneck:
        summary_lines.append(
            f"- Lowest adjacent-stage conversion starts at `{bottleneck[0]}`: {bottleneck[1]:.1%}."
        )
    summary_lines.extend(
        [
            "",
            "Rates use distinct applications reaching each observed stage. Review `data_quality.csv` before using the results, especially when stage history is incomplete or cohorts are immature.",
        ]
    )
    (output_dir / "analysis_summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    manifest = {
        "source_file": input_path.name,
        "as_of_date": as_of.date().isoformat(),
        "source_rows": len(source_rows),
        "valid_event_rows": valid_event_rows,
        "distinct_applications": len(applications),
        "stage_order": stage_order,
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "output_files": list(OUTPUT_FILES),
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="CSV containing one row per application-stage event")
    parser.add_argument("--config", type=Path, required=True, help="JSON-compatible YAML analysis configuration")
    parser.add_argument("--mapping", type=Path, help="Optional JSON-compatible YAML column/stage mapping override")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for aggregate outputs")
    parser.add_argument("--force", action="store_true", help="Replace known generated files in the output directory")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if not args.input.is_file():
            raise FileNotFoundError(f"Input file not found: {args.input}")
        if not args.config.is_file():
            raise FileNotFoundError(f"Config file not found: {args.config}")
        settings = load_json_yaml(args.config)
        if args.mapping:
            if not args.mapping.is_file():
                raise FileNotFoundError(f"Mapping file not found: {args.mapping}")
            settings = merge_settings(settings, load_json_yaml(args.mapping))
        manifest = analyze(args.input, settings, args.output_dir, force=args.force)
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
