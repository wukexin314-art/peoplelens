#!/usr/bin/env python3
"""Profile HR data without printing raw cell values.

Supports CSV, TSV, and XLSX. XLSX support requires openpyxl. The output is an
aggregate JSON report containing schema, missingness, duplicate-key counts,
date-parse issues, and likely sensitive columns.
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


DIRECT_IDENTIFIER_PATTERNS = {
    "employee_or_candidate_id": r"(^|_)(employee|worker|candidate|applicant|erp|person).*(id|number|no)$|^(employee|candidate|worker)_?id$",
    "name": r"(^|_)(employee|candidate|applicant|worker|recruiter|manager)?_?name$|full_?name",
    "email": r"e-?mail|email",
    "phone": r"phone|mobile|telephone",
    "address": r"address|postal|zip_?code",
    "government_id": r"passport|national_?id|social_?security|ssn|tax_?id",
}

SENSITIVE_ATTRIBUTE_PATTERNS = {
    "birth_or_age": r"birth|date_?of_?birth|\bdob\b|\bage\b",
    "gender_or_sex": r"gender|\bsex\b",
    "race_or_ethnicity": r"race|ethnic",
    "nationality_or_citizenship": r"nationality|citizenship",
    "disability_or_health": r"disab|medical|health",
    "religion": r"religion|faith",
    "family_or_marital": r"marital|family_?status|pregnan",
    "sexual_orientation": r"sexual_?orientation",
    "compensation": r"salary|compensation|bonus|pay_?rate|wage",
    "performance_or_discipline": r"performance|rating|disciplin|warning",
    "free_text": r"comment|note|feedback|reason|remark|description",
}

DATE_NAME_RE = re.compile(
    r"(^|_)(date|[a-z0-9_]*_date)($|_)|^(start|hire|join|onboard|leave|separation|termination|effective|opened|closed|accepted|snapshot)$",
    re.I,
)
KNOWN_HR_HEADER_RE = re.compile(
    r"employee|candidate|requisition|offer|hire|join|leave|separation|department|business|source|status|level|grade|recruiter|headcount|target|date",
    re.I,
)


def normalize_header(value: Any, index: int) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        return f"unnamed_{index + 1}"
    return re.sub(r"\s+", "_", text)


def _looks_numeric(value: Any) -> bool:
    try:
        float(str(value).replace(",", ""))
        return True
    except (TypeError, ValueError):
        return False


def detect_header_row(rows: list[list[Any]], explicit: int | None) -> int:
    if explicit is not None:
        if explicit < 1 or explicit > len(rows):
            raise ValueError(f"--header-row must be between 1 and {len(rows)}")
        return explicit - 1
    best_index = 0
    best_score = -1.0
    for index, row in enumerate(rows[:15]):
        cells = [str(v).strip() for v in row if v is not None and str(v).strip()]
        if not cells:
            continue
        unique_ratio = len(set(cells)) / len(cells)
        hr_hits = sum(bool(KNOWN_HR_HEADER_RE.search(cell)) for cell in cells)
        numeric = sum(_looks_numeric(cell) for cell in cells)
        score = len(cells) + unique_ratio * 2 + hr_hits * 4 - numeric * 0.5
        if score > best_score:
            best_index, best_score = index, score
    return best_index


def read_delimited(path: Path, delimiter: str | None) -> tuple[list[list[Any]], str]:
    sample = path.read_text(encoding="utf-8-sig", errors="replace")[:65536]
    if delimiter is None:
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=",\t;|").delimiter
        except csv.Error:
            delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return [list(row) for row in csv.reader(handle, delimiter=delimiter)], delimiter


def read_xlsx(path: Path, sheet: str | None) -> tuple[list[list[Any]], str]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise RuntimeError("XLSX support requires openpyxl. Export to CSV or install openpyxl.") from exc
    workbook = load_workbook(path, read_only=True, data_only=True)
    if sheet is None:
        worksheet = workbook.active
    elif sheet in workbook.sheetnames:
        worksheet = workbook[sheet]
    else:
        raise ValueError(f"Sheet {sheet!r} not found. Available sheets: {', '.join(workbook.sheetnames)}")
    rows = [list(row) for row in worksheet.iter_rows(values_only=True)]
    return rows, worksheet.title


def parse_date(value: Any) -> bool:
    if value is None or value == "":
        return True
    if isinstance(value, (dt.date, dt.datetime)):
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return 1 <= float(value) <= 100000
    text = str(value).strip()
    if not text:
        return True
    formats = (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%b %d, %Y",
        "%B %d, %Y",
    )
    for fmt in formats:
        try:
            dt.datetime.strptime(text, fmt)
            return True
        except ValueError:
            pass
    try:
        dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def detect_columns(headers: list[str], patterns: dict[str, str]) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    for header in headers:
        normalized = re.sub(r"[^a-z0-9]+", "_", header.lower()).strip("_")
        for category, pattern in patterns.items():
            if re.search(pattern, normalized, re.I):
                found.append({"column": header, "category": category})
                break
    return found


def rectangularize(rows: Iterable[list[Any]], width: int) -> list[list[Any]]:
    result = []
    for row in rows:
        padded = list(row[:width])
        padded.extend([None] * (width - len(padded)))
        result.append(padded)
    return result


def profile(
    path: Path,
    sheet: str | None,
    header_row: int | None,
    id_column: str | None,
    delimiter: str | None,
) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix in {".csv", ".tsv", ".txt"}:
        raw_rows, source_detail = read_delimited(path, delimiter)
        source_kind = "delimited"
        source_metadata = {"delimiter": source_detail}
    elif suffix == ".xlsx":
        raw_rows, source_detail = read_xlsx(path, sheet)
        source_kind = "xlsx"
        source_metadata = {"sheet": source_detail}
    elif suffix == ".xls":
        raise RuntimeError("Legacy .xls is not supported. Save it as .xlsx or CSV first.")
    else:
        raise RuntimeError("Supported formats: CSV, TSV, TXT, and XLSX")

    if not raw_rows:
        raise ValueError("The input contains no rows")
    header_index = detect_header_row(raw_rows, header_row)
    original_headers = raw_rows[header_index]
    width = len(original_headers)
    headers = [normalize_header(value, index) for index, value in enumerate(original_headers)]
    data_rows = rectangularize(raw_rows[header_index + 1 :], width)
    data_rows = [row for row in data_rows if any(value not in (None, "") for value in row)]
    row_count = len(data_rows)

    duplicate_headers = sorted(name for name, count in Counter(headers).items() if count > 1)
    columns = []
    for index, header in enumerate(headers):
        values = [row[index] for row in data_rows]
        missing = sum(value is None or str(value).strip() == "" for value in values)
        item: dict[str, Any] = {
            "column": header,
            "missing_count": missing,
            "missing_percent": round((missing / row_count * 100), 1) if row_count else None,
        }
        if DATE_NAME_RE.search(header):
            nonblank = [value for value in values if value is not None and str(value).strip()]
            item["date_parse_failure_count"] = sum(not parse_date(value) for value in nonblank)
        columns.append(item)

    exact_id_header = None
    if id_column:
        lookup = {header.lower(): header for header in headers}
        exact_id_header = lookup.get(id_column.lower())
        if exact_id_header is None:
            raise ValueError(f"ID column {id_column!r} not found")

    duplicate_id_count = None
    blank_id_count = None
    if exact_id_header:
        index = headers.index(exact_id_header)
        ids = [
            str(row[index]).strip()
            for row in data_rows
            if row[index] is not None and str(row[index]).strip()
        ]
        blank_id_count = row_count - len(ids)
        duplicate_id_count = sum(count - 1 for count in Counter(ids).values() if count > 1)

    high_missing = [
        item["column"]
        for item in columns
        if item["missing_percent"] is not None and item["missing_percent"] >= 30
    ]
    all_empty = [item["column"] for item in columns if item["missing_count"] == row_count]
    date_failures = {
        item["column"]: item["date_parse_failure_count"]
        for item in columns
        if item.get("date_parse_failure_count", 0) > 0
    }

    report: dict[str, Any] = {
        "source": {
            "file_name": path.name,
            "format": source_kind,
            **source_metadata,
            "header_row": header_index + 1,
        },
        "shape": {"rows": row_count, "columns": width},
        "schema": headers,
        "columns": columns,
        "privacy_flags": {
            "likely_direct_identifiers": detect_columns(headers, DIRECT_IDENTIFIER_PATTERNS),
            "likely_sensitive_columns": detect_columns(headers, SENSITIVE_ATTRIBUTE_PATTERNS),
            "note": "Header-based detection is heuristic; review before sharing or publishing.",
        },
        "quality_flags": {
            "duplicate_headers": duplicate_headers,
            "all_empty_columns": all_empty,
            "columns_at_least_30_percent_missing": high_missing,
            "date_parse_failures": date_failures,
        },
    }
    if exact_id_header:
        report["id_check"] = {
            "column": exact_id_header,
            "blank_count": blank_id_count,
            "duplicate_row_count": duplicate_id_count,
        }
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="CSV, TSV, TXT, or XLSX file")
    parser.add_argument("--sheet", help="XLSX sheet name; defaults to the active sheet")
    parser.add_argument("--header-row", type=int, help="1-based header row; defaults to auto-detection")
    parser.add_argument("--id-column", help="Column to check for blank and duplicate IDs")
    parser.add_argument("--delimiter", help="Delimiter for text files; defaults to auto-detection")
    parser.add_argument("--output", type=Path, help="Optional JSON output path")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if not args.path.is_file():
            raise FileNotFoundError(f"File not found: {args.path}")
        report = profile(args.path, args.sheet, args.header_row, args.id_column, args.delimiter)
        payload = json.dumps(report, ensure_ascii=False, indent=2)
        if args.output:
            args.output.write_text(payload + "\n", encoding="utf-8")
        print(payload)
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
