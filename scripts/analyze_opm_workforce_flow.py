#!/usr/bin/env python3
"""Analyze OPM FWD accessions and separations Parquet files.

The output is aggregate-only. Net flow is the difference between personnel
actions, not a turnover rate or a substitute for point-in-time headcount.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


OUTPUT_FILES = (
    "monthly_flow.csv",
    "category_summary.csv",
    "segment_summary.csv",
    "data_quality.csv",
    "analysis_summary.md",
    "run_manifest.json",
)


def require_parquet():
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError(
            "OPM Parquet analysis requires pyarrow. Install requirements-parquet.txt."
        ) from exc
    return pq


def parse_month(value: str | None) -> str | None:
    text = (value or "").strip().replace("-", "")
    if not re.fullmatch(r"\d{6}", text):
        return None
    month = int(text[4:])
    return text if 1 <= month <= 12 else None


def display_month(value: str) -> str:
    return f"{value[:4]}-{value[4:]}"


def parse_count(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip().replace(",", "")
    try:
        number = int(text)
    except ValueError:
        return None
    return number if number >= 0 else None


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def quality_row(severity: str, check: str, count: int, detail: str) -> dict[str, Any]:
    return {"severity": severity, "check": check, "count": count, "detail": detail}


def consume_file(
    path: Path,
    kind: str,
    category_column: str,
    segments: list[str],
    start_month: str | None,
    end_month: str | None,
) -> dict[str, Any]:
    pq = require_parquet()
    parquet = pq.ParquetFile(path)
    required = {"count", "personnel_action_effective_date_yyyymm", category_column, *segments}
    missing = sorted(required - set(parquet.schema_arrow.names))
    if missing:
        raise ValueError(f"{path.name} is missing required OPM columns: {', '.join(missing)}")

    columns = ["count", "personnel_action_effective_date_yyyymm", category_column, *segments]
    monthly: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    segment_counts: Counter[tuple[str, str]] = Counter()
    issues: Counter[str] = Counter()
    source_rows = 0
    included_rows = 0

    for batch in parquet.iter_batches(columns=columns, batch_size=65536):
        values = batch.to_pydict()
        for index in range(batch.num_rows):
            source_rows += 1
            count = parse_count(values["count"][index])
            if count is None:
                issues["invalid_count"] += 1
                continue
            month = parse_month(values["personnel_action_effective_date_yyyymm"][index])
            if month is None:
                issues["invalid_effective_month"] += 1
                continue
            if (start_month and month < start_month) or (end_month and month > end_month):
                issues["outside_period"] += 1
                continue
            included_rows += 1
            monthly[month] += count
            category = str(values[category_column][index] or "").strip() or "Unknown"
            if category == "Unknown":
                issues["blank_category"] += 1
            categories[category] += count
            for segment in segments:
                value = str(values[segment][index] or "").strip() or "Unknown"
                if value == "Unknown":
                    issues[f"blank_segment:{segment}"] += 1
                segment_counts[(segment, value)] += count

    return {
        "kind": kind,
        "source_rows": source_rows,
        "included_rows": included_rows,
        "monthly": monthly,
        "categories": categories,
        "segments": segment_counts,
        "issues": issues,
    }


def analyze(
    accessions_path: Path,
    separations_path: Path,
    output_dir: Path,
    start_month: str | None = None,
    end_month: str | None = None,
    segments: list[str] | None = None,
    minimum_cell_size: int = 5,
    force: bool = False,
) -> dict[str, Any]:
    start = parse_month(start_month) if start_month else None
    end = parse_month(end_month) if end_month else None
    if start_month and start is None:
        raise ValueError("--start-month must use YYYY-MM")
    if end_month and end is None:
        raise ValueError("--end-month must use YYYY-MM")
    if start and end and start > end:
        raise ValueError("--start-month cannot be after --end-month")
    if minimum_cell_size < 1:
        raise ValueError("--minimum-cell-size must be positive")
    segments = list(dict.fromkeys(segments or ["department"]))

    output_dir.mkdir(parents=True, exist_ok=True)
    existing = [name for name in OUTPUT_FILES if (output_dir / name).exists()]
    if existing and not force:
        raise FileExistsError(
            f"Output files already exist: {', '.join(existing)}. Use --force to replace them."
        )

    accessions = consume_file(
        accessions_path, "accessions", "accession_category", segments, start, end
    )
    separations = consume_file(
        separations_path, "separations", "separation_category", segments, start, end
    )

    months = sorted(set(accessions["monthly"]) | set(separations["monthly"]))
    monthly_rows = [
        {
            "effective_month": display_month(month),
            "accessions": accessions["monthly"][month],
            "separations": separations["monthly"][month],
            "net_action_flow": accessions["monthly"][month] - separations["monthly"][month],
        }
        for month in months
    ]
    write_csv(
        output_dir / "monthly_flow.csv",
        ["effective_month", "accessions", "separations", "net_action_flow"],
        monthly_rows,
    )

    category_rows = []
    for result in (accessions, separations):
        total = sum(result["categories"].values())
        for category, count in sorted(result["categories"].items(), key=lambda item: (-item[1], item[0])):
            category_rows.append(
                {
                    "event_type": result["kind"],
                    "category": category,
                    "action_count": count,
                    "share_of_event_type": f"{count / total:.4f}" if total else "",
                }
            )
    write_csv(
        output_dir / "category_summary.csv",
        ["event_type", "category", "action_count", "share_of_event_type"],
        category_rows,
    )

    segment_rows = []
    for segment in segments:
        values = sorted(
            {value for name, value in accessions["segments"] if name == segment}
            | {value for name, value in separations["segments"] if name == segment}
        )
        groups = []
        for value in values:
            accession_count = accessions["segments"][(segment, value)]
            separation_count = separations["segments"][(segment, value)]
            small = (
                accession_count + separation_count < minimum_cell_size
                or 0 < accession_count < minimum_cell_size
                or 0 < separation_count < minimum_cell_size
            )
            groups.append(
                {
                    "value": value,
                    "accessions": accession_count,
                    "separations": separation_count,
                    "suppression_reason": "small_cell" if small else "",
                }
            )
        suppressed = [group for group in groups if group["suppression_reason"]]
        if len(suppressed) == 1 and len(groups) > 1:
            secondary = min(
                (group for group in groups if not group["suppression_reason"]),
                key=lambda group: group["accessions"] + group["separations"],
            )
            secondary["suppression_reason"] = "complementary"
        for group in groups:
            hidden = bool(group["suppression_reason"])
            segment_rows.append(
                {
                    "segment": segment,
                    "value": group["value"],
                    "accessions": "" if hidden else group["accessions"],
                    "separations": "" if hidden else group["separations"],
                    "net_action_flow": "" if hidden else group["accessions"] - group["separations"],
                    "suppressed": str(hidden).lower(),
                    "suppression_reason": group["suppression_reason"],
                    "minimum_cell_size": minimum_cell_size,
                }
            )
    write_csv(
        output_dir / "segment_summary.csv",
        [
            "segment",
            "value",
            "accessions",
            "separations",
            "net_action_flow",
            "suppressed",
            "suppression_reason",
            "minimum_cell_size",
        ],
        segment_rows,
    )

    issues = accessions["issues"] + separations["issues"]
    blank_segment_rows = sum(count for key, count in issues.items() if key.startswith("blank_segment:"))
    quality_rows = [
        quality_row("error", "invalid_count", issues["invalid_count"], "Rows excluded because count is not a non-negative integer."),
        quality_row("error", "invalid_effective_month", issues["invalid_effective_month"], "Rows excluded because the effective month is invalid."),
        quality_row("info", "outside_period", issues["outside_period"], "Rows excluded by the requested effective-month window."),
        quality_row("warning", "blank_category", issues["blank_category"], "Included rows whose action category was reported as Unknown."),
        quality_row("warning", "blank_segment", blank_segment_rows, "Included rows with an Unknown configured segment value."),
    ]
    write_csv(output_dir / "data_quality.csv", ["severity", "check", "count", "detail"], quality_rows)

    total_accessions = sum(accessions["monthly"].values())
    total_separations = sum(separations["monthly"].values())
    summary = [
        "# OPM workforce flow summary",
        "",
        f"- Effective-month window: {display_month(start) if start else 'all available'} to {display_month(end) if end else 'all available'}",
        f"- Accessions: {total_accessions:,}",
        f"- Separations: {total_separations:,}",
        f"- Net personnel-action flow: {total_accessions - total_separations:+,}",
        f"- Source rows: {accessions['source_rows'] + separations['source_rows']:,}",
        f"- Rows excluded outside the period: {issues['outside_period']:,}",
        f"- Suppressed segment rows: {sum(row['suppressed'] == 'true' for row in segment_rows):,}",
        "",
        "Net personnel-action flow is accessions minus separations. It is not headcount growth or turnover because these files do not provide average headcount and include transfer actions. Filter on effective month to separate the requested period from late-reported actions.",
    ]
    (output_dir / "analysis_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    manifest = {
        "accessions_file": accessions_path.name,
        "separations_file": separations_path.name,
        "start_month": display_month(start) if start else None,
        "end_month": display_month(end) if end else None,
        "source_rows": accessions["source_rows"] + separations["source_rows"],
        "included_rows": accessions["included_rows"] + separations["included_rows"],
        "accessions": total_accessions,
        "separations": total_separations,
        "net_action_flow": total_accessions - total_separations,
        "segments": segments,
        "minimum_cell_size": minimum_cell_size,
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "output_files": list(OUTPUT_FILES),
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accessions", type=Path, required=True, help="OPM accessions Parquet file")
    parser.add_argument("--separations", type=Path, required=True, help="OPM separations Parquet file")
    parser.add_argument("--start-month", help="First effective month, YYYY-MM")
    parser.add_argument("--end-month", help="Last effective month, YYYY-MM")
    parser.add_argument("--group-by", action="append", dest="segments", help="Shared OPM column to aggregate; repeat for multiple segments")
    parser.add_argument("--minimum-cell-size", type=int, default=5, help="Minimum non-zero aggregate cell size; defaults to 5")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for aggregate outputs")
    parser.add_argument("--force", action="store_true", help="Replace known generated files in the output directory")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        for path in (args.accessions, args.separations):
            if not path.is_file():
                raise FileNotFoundError(f"Input file not found: {path}")
        manifest = analyze(
            args.accessions,
            args.separations,
            args.output_dir,
            start_month=args.start_month,
            end_month=args.end_month,
            segments=args.segments,
            minimum_cell_size=args.minimum_cell_size,
            force=args.force,
        )
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
