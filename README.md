# PeopleLens

A privacy-aware Codex skill for recruiting and workforce analytics.

[简体中文](README.zh-CN.md)

It turns recurring HR workflows into a consistent analysis method: inspect and reconcile trackers, define metrics before calculating them, analyze hiring and workforce outcomes, and produce decision-ready dashboards or reports with an audit trail.

## What it covers

- Headcount and workforce movement
- Hiring targets and completion pacing
- Recruiting funnel conversion, drop-off, stage aging, and backlog
- Requisition aging, time to fill, time to hire, and recruiting SLA
- Source-of-hire and referral trends
- Offer and requisition status normalization
- Turnover, 60-day early attrition, and probation retention
- Internal mobility, promotions, workforce mix, FTE, and plan variance
- Business-unit, level, source, and recruiter breakdowns
- Workbook reconciliation with before/after change logs
- Data-quality, privacy, and small-cell checks

The skill is designed for aggregate analysis. It does **not** rank candidates or employees and does not make individual employment decisions.

## Use

Place this folder in a location your Codex setup uses for skills, then invoke `$peoplelens` with a request such as:

- “Audit these HR workbooks and propose a canonical data model.”
- “Calculate 60-day attrition by business unit using mature cohorts.”
- “Analyze application-to-start funnel conversion, drop-off, and time in stage by hiring cohort.”
- “Reconcile this ATS export with the headcount tracker and create a change log.”
- “Build a monthly hiring and retention report with definitions and QA notes.”

The skill can also be selected automatically for relevant HR analytics requests.

## Executable recruiting funnel

PeopleLens includes a zero-dependency analyzer for ATS stage-event CSV exports:

```bash
python3 scripts/analyze_recruiting_funnel.py \
  examples/recruiting-funnel/applications.csv \
  --config configs/recruiting-funnel.example.yaml \
  --mapping configs/mappings/canonical-event-history.yaml \
  --output-dir /tmp/peoplelens-output
```

It produces cohort-safe funnel conversion, cumulative yield, terminal outcomes, stage duration, active backlog, aging bands, privacy-suppressed segment cuts, mapping diagnostics, configured metrics, an automatic data-quality report, a metric dictionary, and a run manifest. See [the synthetic example](examples/recruiting-funnel/README.md) and its committed standard output.

Funnel rates use applications from the configured entry cohort that have reached the minimum follow-up window. Adjacent conversion requires the same application to reach the next stage in chronological order. Events after the as-of timestamp are excluded, and stage exits after that timestamp remain open for backlog purposes. Override the configured date when needed with `--as-of-date YYYY-MM-DD`.

Segment outputs suppress small cells using `minimum_cell_size` (default `5`). `mapping_report.csv` lists mapped and unmapped source stages without candidate-level values, while `cohort_summary.csv` records the cohort window and maturity counts.

Configuration files use JSON-compatible YAML and can be edited without adding Python dependencies. Mapping starters are provided for canonical event history, human-readable headers, and a generic ATS status log. They are templates, not vendor guarantees; confirm every field and stage mapping against the actual export.

## Local structural audit

The included profiler inspects schema, missingness, duplicate IDs, date parsing, and likely sensitive columns without printing raw cell values:

```bash
python3 scripts/profile_hr_data.py sample.csv --id-column employee_id
python3 scripts/profile_hr_data.py workbook.xlsx --sheet "Employees" --id-column worker_id
python3 scripts/profile_hr_data.py workforce.parquet --id-column employee_id
```

CSV and TSV use only the Python standard library. XLSX support requires `openpyxl`; Parquet support requires `pyarrow` from `requirements-parquet.txt`. Parquet files are processed in batches rather than loaded fully into memory.

## OPM workforce flow

PeopleLens can analyze versioned OPM Federal Workforce Data accessions and separations files:

```bash
python3 -m pip install -r requirements-parquet.txt
python3 scripts/analyze_opm_workforce_flow.py \
  --accessions accessions_202608_1.parquet \
  --separations separations_202608_1.parquet \
  --start-month 2026-08 \
  --end-month 2026-08 \
  --group-by department \
  --output-dir /tmp/peoplelens-opm-output
```

The analyzer produces monthly action flow, accession and separation category mix, privacy-suppressed segment results, data-quality checks, a concise summary, and a run manifest. Net action flow is deliberately not labeled headcount growth or turnover. See [the public-data validation pack](examples/public-data-validation/README.md).

## Repository structure

```text
.
|-- SKILL.md
|-- agents/openai.yaml
|-- scripts/
|   |-- profile_hr_data.py
|   |-- analyze_recruiting_funnel.py
|   `-- analyze_opm_workforce_flow.py
|-- configs/
|   |-- recruiting-funnel.example.yaml
|   `-- mappings/
|-- examples/
|   |-- recruiting-funnel/
|   `-- public-data-validation/
|-- references/
|   |-- data-contract.md
|   |-- metrics.md
|   |-- recruiting-funnel.md
|   |-- workforce-flow.md
|   |-- privacy.md
|   `-- reporting.md
`-- assets/
    |-- analysis-brief-template.md
    `-- metric-dictionary-template.csv
```

Run the test suite with:

```bash
python3 -m pip install -r requirements-parquet.txt
python3 -m unittest discover -s tests
```

## Privacy

No company data, employee records, internal mappings, personal names, targets, or local file paths are included. All examples are synthetic. Review your organization's privacy, legal, and works-council requirements before using real HR data.

## License

MIT
