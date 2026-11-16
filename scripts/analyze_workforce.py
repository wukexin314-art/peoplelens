#!/usr/bin/env python3
"""Analyze employee-spell CSV data and produce privacy-aware workforce metrics."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
import tempfile
from collections import Counter
from functools import wraps
from pathlib import Path
from typing import Any, Iterable


OUTPUT_FILES = (
    "workforce_metrics.csv",
    "segment_summary.csv",
    "separation_summary.csv",
    "cohort_summary.csv",
    "data_quality.csv",
    "metric_dictionary.csv",
    "analysis_summary.md",
    "run_manifest.json",
)


def staged_outputs(function):
    @wraps(function)
    def wrapper(input_path: Path, settings: dict[str, Any], output_dir: Path, force: bool = False):
        existing = [name for name in OUTPUT_FILES if (output_dir / name).exists()]
        if existing and not force:
            raise FileExistsError(
                f"Output files already exist: {', '.join(existing)}. Use --force to replace them."
            )
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=f".{output_dir.name}-", dir=output_dir.parent) as directory:
            write_dir = Path(directory)
            manifest = function(input_path, settings, write_dir, force)
            output_dir.mkdir(parents=True, exist_ok=True)
            for name in OUTPUT_FILES:
                (write_dir / name).replace(output_dir / name)
            return manifest

    return wrapper


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


def parse_date(value: str) -> dt.date | None:
    text = value.strip()
    if not text:
        return None
    try:
        return dt.date.fromisoformat(text)
    except ValueError:
        return None


def parse_fte(value: str, default: float) -> float | None:
    if not value.strip():
        return default
    try:
        parsed = float(value.replace(",", ""))
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


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


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def format_rate(numerator: float, denominator: float) -> str:
    return f"{numerator / denominator:.4f}" if denominator else ""


def is_active(spell: dict[str, Any], as_of: dt.date) -> bool:
    return spell["hire_date"] <= as_of and (
        spell["separation_date"] is None or spell["separation_date"] > as_of
    )


def should_suppress(values: Iterable[float], minimum: int) -> bool:
    return any(0 < value < minimum for value in values)


def validate_settings(settings: dict[str, Any], headers: list[str]) -> dict[str, Any]:
    columns = settings.get("columns")
    if not isinstance(columns, dict):
        raise ValueError("Configuration requires a columns object")
    for canonical in ("employee_id", "hire_date"):
        source = columns.get(canonical)
        if not source:
            raise ValueError(f"Missing required column mapping: {canonical}")
        if source not in headers:
            raise ValueError(f"Mapped input column not found: {source}")
    for canonical, source in columns.items():
        if source and source not in headers:
            raise ValueError(f"Mapped input column not found for {canonical}: {source}")

    as_of = parse_date(str(settings.get("as_of_date", "")))
    period_start = parse_date(str(settings.get("period_start", "")))
    period_end = parse_date(str(settings.get("period_end", "")))
    if not as_of or not period_start or not period_end:
        raise ValueError("as_of_date, period_start, and period_end must use YYYY-MM-DD")
    if period_start > period_end:
        raise ValueError("period_start cannot be after period_end")
    if period_end > as_of:
        raise ValueError("period_end cannot be after as_of_date")
    early_days = settings.get("early_attrition_days", 60)
    minimum = settings.get("minimum_cell_size", 5)
    default_fte = settings.get("default_fte", 1.0)
    if not isinstance(early_days, int) or early_days < 1:
        raise ValueError("early_attrition_days must be a positive integer")
    if not isinstance(minimum, int) or minimum < 1:
        raise ValueError("minimum_cell_size must be a positive integer")
    if not isinstance(default_fte, (int, float)) or default_fte < 0:
        raise ValueError("default_fte must be a non-negative number")
    return {
        "as_of": as_of,
        "period_start": period_start,
        "period_end": period_end,
        "opening_date": period_start - dt.timedelta(days=1),
        "early_days": early_days,
        "minimum": minimum,
        "default_fte": float(default_fte),
    }


@staged_outputs
def analyze(
    input_path: Path,
    settings: dict[str, Any],
    output_dir: Path,
    force: bool = False,
) -> dict[str, Any]:
    headers, source_rows = read_rows(input_path)
    dates = validate_settings(settings, headers)
    write_dir = output_dir

    columns: dict[str, str] = settings["columns"]
    segments = list(dict.fromkeys(settings.get("segments", [])))
    voluntary_values = {str(value).strip().casefold() for value in settings.get("voluntary_separation_values", [])}
    involuntary_values = {str(value).strip().casefold() for value in settings.get("involuntary_separation_values", [])}

    def cell(row: dict[str, str], canonical: str) -> str:
        source = columns.get(canonical, "")
        return row.get(source, "") if source else ""

    issues: Counter[str] = Counter()
    spells_by_key: dict[tuple[str, dt.date], dict[str, Any]] = {}
    for row in source_rows:
        employee_id = cell(row, "employee_id")
        hire_date = parse_date(cell(row, "hire_date"))
        separation_text = cell(row, "separation_date")
        separation_date = parse_date(separation_text) if separation_text else None
        if not employee_id:
            issues["missing_employee_id"] += 1
            continue
        if hire_date is None:
            issues["invalid_hire_date"] += 1
            continue
        if hire_date > dates["as_of"]:
            issues["future_hire_date"] += 1
            continue
        if separation_text and separation_date is None:
            issues["invalid_separation_date"] += 1
            continue
        if separation_date and separation_date < hire_date:
            issues["separation_before_hire"] += 1
            continue
        if separation_date and separation_date > dates["as_of"]:
            issues["future_separation_date"] += 1
            separation_date = None
        fte = parse_fte(cell(row, "fte"), dates["default_fte"])
        if fte is None:
            issues["invalid_fte"] += 1
            fte = 0.0
        key = (employee_id, hire_date)
        if key in spells_by_key:
            issues["duplicate_employment_spell"] += 1
            continue
        spells_by_key[key] = {
            "employee_id": employee_id,
            "hire_date": hire_date,
            "separation_date": separation_date,
            "separation_type": cell(row, "separation_type") or "Unknown",
            "fte": fte,
            "segments": {segment: cell(row, segment) or "Unknown" for segment in segments},
        }

    spells = list(spells_by_key.values())
    opening = [spell for spell in spells if is_active(spell, dates["opening_date"])]
    closing = [spell for spell in spells if is_active(spell, dates["period_end"])]
    hires = [spell for spell in spells if dates["period_start"] <= spell["hire_date"] <= dates["period_end"]]
    separations = [
        spell for spell in spells
        if spell["separation_date"] and dates["period_start"] <= spell["separation_date"] <= dates["period_end"]
    ]
    average_headcount = (len(opening) + len(closing)) / 2
    net_change = len(closing) - len(opening)
    voluntary = sum(spell["separation_type"].casefold() in voluntary_values for spell in separations)
    involuntary = sum(spell["separation_type"].casefold() in involuntary_values for spell in separations)
    unclassified = len(separations) - voluntary - involuntary

    mature_cutoff = dates["as_of"] - dt.timedelta(days=dates["early_days"])
    hire_cohort = hires
    mature_hires = [spell for spell in hire_cohort if spell["hire_date"] <= mature_cutoff]
    early_separations = [
        spell for spell in mature_hires
        if spell["separation_date"]
        and spell["separation_date"] <= spell["hire_date"] + dt.timedelta(days=dates["early_days"])
    ]

    metrics = [
        ("opening_headcount", len(opening), len(opening), None),
        ("closing_headcount", len(closing), len(closing), None),
        ("period_hires", len(hires), len(hires), None),
        ("period_separations", len(separations), len(separations), None),
        ("net_headcount_change", net_change, net_change, None),
        ("headcount_growth_rate", format_rate(net_change, len(opening)), net_change, len(opening)),
        ("average_headcount_approximation", f"{average_headcount:.2f}", len(opening) + len(closing), 2),
        ("turnover_rate", format_rate(len(separations), average_headcount), len(separations), average_headcount),
        ("voluntary_turnover_rate", format_rate(voluntary, average_headcount), voluntary, average_headcount),
        ("involuntary_turnover_rate", format_rate(involuntary, average_headcount), involuntary, average_headcount),
        ("closing_fte", f"{sum(spell['fte'] for spell in closing):.2f}", None, None),
        (f"early_attrition_{dates['early_days']}_day_rate", format_rate(len(early_separations), len(mature_hires)), len(early_separations), len(mature_hires)),
        (f"retention_{dates['early_days']}_day_rate", format_rate(len(mature_hires) - len(early_separations), len(mature_hires)), len(mature_hires) - len(early_separations), len(mature_hires)),
    ]
    metric_rows = [
        {
            "metric_name": name,
            "value": value,
            "numerator": "" if numerator is None else numerator,
            "denominator": "" if denominator is None else denominator,
            "period_start": dates["period_start"].isoformat(),
            "period_end": dates["period_end"].isoformat(),
            "as_of_date": dates["as_of"].isoformat(),
        }
        for name, value, numerator, denominator in metrics
    ]
    write_csv(
        write_dir / "workforce_metrics.csv",
        ["metric_name", "value", "numerator", "denominator", "period_start", "period_end", "as_of_date"],
        metric_rows,
    )

    segment_rows = []
    for segment in segments:
        values = sorted({spell["segments"][segment] for spell in spells})
        groups = []
        for value in values:
            group_opening = sum(spell["segments"][segment] == value for spell in opening)
            group_closing = sum(spell["segments"][segment] == value for spell in closing)
            group_hires = sum(spell["segments"][segment] == value for spell in hires)
            group_separations = sum(spell["segments"][segment] == value for spell in separations)
            group_average = (group_opening + group_closing) / 2
            groups.append(
                {
                    "segment": segment,
                    "value": value,
                    "opening": group_opening,
                    "closing": group_closing,
                    "hires": group_hires,
                    "separations": group_separations,
                    "average": group_average,
                    "suppression_reason": "small_cell" if should_suppress(
                        (group_opening, group_closing, group_hires, group_separations), dates["minimum"]
                    ) else "",
                }
            )
        suppressed = [group for group in groups if group["suppression_reason"]]
        if len(suppressed) == 1 and len(groups) > 1:
            visible = [group for group in groups if not group["suppression_reason"]]
            if visible:
                min(visible, key=lambda group: group["opening"] + group["closing"])["suppression_reason"] = "complementary"
        for group in groups:
            hidden = bool(group["suppression_reason"])
            segment_rows.append(
                {
                    "segment": segment,
                    "value": group["value"],
                    "opening_headcount": "" if hidden else group["opening"],
                    "closing_headcount": "" if hidden else group["closing"],
                    "period_hires": "" if hidden else group["hires"],
                    "period_separations": "" if hidden else group["separations"],
                    "turnover_rate": "" if hidden else format_rate(group["separations"], group["average"]),
                    "suppressed": str(hidden).lower(),
                    "suppression_reason": group["suppression_reason"],
                    "minimum_cell_size": dates["minimum"],
                }
            )
    write_csv(
        write_dir / "segment_summary.csv",
        ["segment", "value", "opening_headcount", "closing_headcount", "period_hires", "period_separations", "turnover_rate", "suppressed", "suppression_reason", "minimum_cell_size"],
        segment_rows,
    )

    separation_counts = Counter(spell["separation_type"] for spell in separations)
    separation_groups = [
        {
            "value": value,
            "count": count,
            "suppression_reason": "small_cell" if 0 < count < dates["minimum"] else "",
        }
        for value, count in sorted(separation_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    suppressed_separations = [group for group in separation_groups if group["suppression_reason"]]
    if len(suppressed_separations) == 1 and len(separation_groups) > 1:
        visible = [group for group in separation_groups if not group["suppression_reason"]]
        if visible:
            min(visible, key=lambda group: group["count"])["suppression_reason"] = "complementary"
    separation_rows = []
    for group in separation_groups:
        hidden = bool(group["suppression_reason"])
        separation_rows.append(
            {
                "separation_type": group["value"],
                "separation_count": "" if hidden else group["count"],
                "share_of_separations": "" if hidden else format_rate(group["count"], len(separations)),
                "suppressed": str(hidden).lower(),
                "suppression_reason": group["suppression_reason"],
                "minimum_cell_size": dates["minimum"],
            }
        )
    write_csv(
        write_dir / "separation_summary.csv",
        ["separation_type", "separation_count", "share_of_separations", "suppressed", "suppression_reason", "minimum_cell_size"],
        separation_rows,
    )

    cohort_rows = [{
        "cohort_start": dates["period_start"].isoformat(),
        "cohort_end": dates["period_end"].isoformat(),
        "milestone_days": dates["early_days"],
        "cohort_hires": len(hire_cohort),
        "mature_hires": len(mature_hires),
        "immature_hires": len(hire_cohort) - len(mature_hires),
        "early_separations": len(early_separations),
        "early_attrition_rate": format_rate(len(early_separations), len(mature_hires)),
        "milestone_retention_rate": format_rate(len(mature_hires) - len(early_separations), len(mature_hires)),
    }]
    write_csv(write_dir / "cohort_summary.csv", list(cohort_rows[0]), cohort_rows)

    quality_rows = [
        {"severity": "error", "check": "missing_employee_id", "count": issues["missing_employee_id"], "detail": "Rows excluded because employee_id is blank."},
        {"severity": "error", "check": "invalid_hire_date", "count": issues["invalid_hire_date"], "detail": "Rows excluded because hire_date is invalid."},
        {"severity": "error", "check": "invalid_separation_date", "count": issues["invalid_separation_date"], "detail": "Rows excluded because separation_date is invalid."},
        {"severity": "error", "check": "separation_before_hire", "count": issues["separation_before_hire"], "detail": "Rows excluded because separation precedes hire."},
        {"severity": "warning", "check": "duplicate_employment_spell", "count": issues["duplicate_employment_spell"], "detail": "Duplicate employee_id and hire_date spells were counted once."},
        {"severity": "warning", "check": "future_hire_date", "count": issues["future_hire_date"], "detail": "Rows with hire dates after as_of_date were excluded."},
        {"severity": "warning", "check": "future_separation_date", "count": issues["future_separation_date"], "detail": "Future separations were treated as not yet separated."},
        {"severity": "warning", "check": "invalid_fte", "count": issues["invalid_fte"], "detail": "Invalid FTE values were excluded from FTE totals."},
        {"severity": "info", "check": "unclassified_separations", "count": unclassified, "detail": "Period separations not mapped to configured voluntary or involuntary values."},
    ]
    write_csv(write_dir / "data_quality.csv", ["severity", "check", "count", "detail"], quality_rows)

    dictionary_rows = [
        {"metric_name": "opening_headcount", "definition": "Distinct active employment spells on the day before period_start.", "known_limitations": "Employment spells require stable employee_id and hire_date."},
        {"metric_name": "closing_headcount", "definition": "Distinct active employment spells on period_end.", "known_limitations": "Effective-dated organizational movement is not inferred."},
        {"metric_name": "turnover_rate", "definition": "Period separations divided by the mean of opening and closing headcount.", "known_limitations": "Average headcount is an opening/closing approximation."},
        {"metric_name": f"early_attrition_{dates['early_days']}_day_rate", "definition": f"Mature period hires separating within {dates['early_days']} days divided by mature period hires.", "known_limitations": "Latest hires are excluded until the full milestone window is observable."},
        {"metric_name": "closing_fte", "definition": "Sum of configured FTE for active closing employment spells.", "known_limitations": f"Blank FTE defaults to {dates['default_fte']:.2f}; invalid values contribute zero."},
    ]
    write_csv(write_dir / "metric_dictionary.csv", ["metric_name", "definition", "known_limitations"], dictionary_rows)

    summary = [
        "# Workforce summary",
        "",
        f"- Reporting period: {dates['period_start'].isoformat()} to {dates['period_end'].isoformat()}",
        f"- Opening headcount: {len(opening):,}; closing headcount: {len(closing):,}; net change: {net_change:+,}",
        f"- Hires: {len(hires):,}; separations: {len(separations):,}; turnover rate: {format_rate(len(separations), average_headcount) or 'N/A'}",
        f"- Closing FTE: {sum(spell['fte'] for spell in closing):,.2f}",
        f"- {dates['early_days']}-day mature hire cohort: {len(mature_hires):,}; early separations: {len(early_separations):,}; retention: {format_rate(len(mature_hires) - len(early_separations), len(mature_hires)) or 'N/A'}",
        f"- Source rows: {len(source_rows):,}; valid employment spells: {len(spells):,}",
        "",
        "Turnover uses the mean of opening and closing headcount as an approximation. Segment metrics use the segment value stored on each employment-spell row and do not reconstruct effective-dated organizational movement.",
    ]
    (write_dir / "analysis_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    manifest = {
        "input_file": input_path.name,
        "input_grain": "employment_spell",
        "source_rows": len(source_rows),
        "valid_employment_spells": len(spells),
        "period_start": dates["period_start"].isoformat(),
        "period_end": dates["period_end"].isoformat(),
        "as_of_date": dates["as_of"].isoformat(),
        "segments": segments,
        "minimum_cell_size": dates["minimum"],
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "output_files": list(OUTPUT_FILES),
    }
    (write_dir / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Employee-spell CSV file")
    parser.add_argument("--config", type=Path, required=True, help="JSON-compatible YAML configuration")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for aggregate outputs")
    parser.add_argument("--as-of-date", help="Override the configured as-of date, YYYY-MM-DD")
    parser.add_argument("--force", action="store_true", help="Replace known generated files")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if not args.input.is_file():
            raise FileNotFoundError(f"Input file not found: {args.input}")
        settings = load_json_yaml(args.config)
        if args.as_of_date:
            settings["as_of_date"] = args.as_of_date
        manifest = analyze(args.input, settings, args.output_dir, args.force)
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
