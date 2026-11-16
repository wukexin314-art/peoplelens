#!/usr/bin/env python3
"""Normalize a Greenhouse Analytics application-stage-changes CSV for PeopleLens."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import tempfile
from pathlib import Path


OUTPUT_COLUMNS = (
    "application_id",
    "candidate_id",
    "requisition_id",
    "business_unit",
    "job_level",
    "source",
    "recruiter",
    "stage",
    "stage_entered_at",
    "stage_exited_at",
    "stage_outcome",
)

ALIASES = {
    "application_id": ("Application ID",),
    "candidate_id": ("Candidate ID",),
    "requisition_id": ("Requisition ID", "Job Requisition ID", "Req ID"),
    "business_unit": ("Department", "Department Name"),
    "job_level": ("Job Level", "Grade"),
    "source": ("Source", "Application Source", "Application Source Name"),
    "recruiter": ("Recruiter", "Recruiter Name", "Primary Recruiter"),
    "stage": ("Application Stage Name", "Stage Name", "Stage"),
    "stage_entered_at": ("Application Stage Entered At", "Stage Entered At"),
    "stage_exited_at": ("Application Stage Exited At", "Stage Exited At"),
    "stage_outcome": ("Stage Outcome", "Application Stage Outcome"),
}


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def parse_overrides(values: list[str]) -> dict[str, str]:
    overrides = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--column must use canonical=source_header")
        canonical, source = (part.strip() for part in value.split("=", 1))
        if canonical not in OUTPUT_COLUMNS:
            raise ValueError(f"Unknown canonical column: {canonical}")
        if not source:
            raise ValueError(f"Source header cannot be blank for {canonical}")
        overrides[canonical] = source
    return overrides


def resolve_columns(headers: list[str], overrides: dict[str, str]) -> dict[str, str]:
    lookup = {normalized(header): header for header in headers}
    resolved = {}
    for canonical in OUTPUT_COLUMNS:
        choices = (overrides[canonical],) if canonical in overrides else ALIASES[canonical]
        source = next((lookup.get(normalized(choice)) for choice in choices if normalized(choice) in lookup), None)
        if source:
            resolved[canonical] = source
    missing = [name for name in ("application_id", "stage", "stage_entered_at") if name not in resolved]
    if missing:
        raise ValueError(
            "Missing required Greenhouse stage-change fields: " + ", ".join(missing)
            + ". Use --column canonical=source_header to map custom labels."
        )
    return resolved


def adapt(input_path: Path, output_path: Path, overrides: dict[str, str], force: bool = False) -> dict[str, object]:
    if output_path.exists() and not force:
        raise FileExistsError(f"Output already exists: {output_path}. Use --force to replace it.")
    with input_path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("The input CSV has no header row")
        headers = [header.strip() for header in reader.fieldnames]
        resolved = resolve_columns(headers, overrides)
        rows = []
        skipped = 0
        for raw in reader:
            row = {name: (raw.get(source) or "").strip() for name, source in resolved.items()}
            if not row.get("application_id") or not row.get("stage") or not row.get("stage_entered_at"):
                skipped += 1
                continue
            rows.append({name: row.get(name, "") for name in OUTPUT_COLUMNS})

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{output_path.stem}-", dir=output_path.parent) as directory:
        staged = Path(directory) / output_path.name
        with staged.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        staged.replace(output_path)
    return {
        "input_file": input_path.name,
        "output_file": output_path.name,
        "source_rows": len(rows) + skipped,
        "output_rows": len(rows),
        "skipped_missing_required_fields": skipped,
        "resolved_columns": resolved,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Greenhouse Application stage changes CSV")
    parser.add_argument("--output", type=Path, required=True, help="Canonical stage-event CSV")
    parser.add_argument("--column", action="append", default=[], help="Override a header as canonical=source_header")
    parser.add_argument("--force", action="store_true", help="Replace the output file")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if not args.input.is_file():
            raise FileNotFoundError(f"Input file not found: {args.input}")
        manifest = adapt(args.input, args.output, parse_overrides(args.column), args.force)
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
