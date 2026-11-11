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

It produces funnel conversion, cumulative yield, terminal outcomes, stage duration, active backlog, aging bands, configured metrics, segment cuts, an automatic data-quality report, a metric dictionary, and a run manifest. See [the synthetic example](examples/recruiting-funnel/README.md) and its committed standard output.

Configuration files use JSON-compatible YAML and can be edited without adding Python dependencies. Mapping starters are provided for canonical event history, human-readable headers, and a generic ATS status log. They are templates, not vendor guarantees; confirm every field and stage mapping against the actual export.

## Local structural audit

The included profiler inspects schema, missingness, duplicate IDs, date parsing, and likely sensitive columns without printing raw cell values:

```bash
python3 scripts/profile_hr_data.py sample.csv --id-column employee_id
python3 scripts/profile_hr_data.py workbook.xlsx --sheet "Employees" --id-column worker_id
```

CSV and TSV use only the Python standard library. XLSX support requires `openpyxl`.

## Repository structure

```text
.
|-- SKILL.md
|-- agents/openai.yaml
|-- scripts/
|   |-- profile_hr_data.py
|   `-- analyze_recruiting_funnel.py
|-- configs/
|   |-- recruiting-funnel.example.yaml
|   `-- mappings/
|-- examples/recruiting-funnel/
|   |-- applications.csv
|   `-- output/
|-- references/
|   |-- data-contract.md
|   |-- metrics.md
|   |-- recruiting-funnel.md
|   |-- privacy.md
|   `-- reporting.md
`-- assets/
    |-- analysis-brief-template.md
    `-- metric-dictionary-template.csv
```

Run the standard-library test with:

```bash
python3 -m unittest discover -s tests
```

## Privacy

No company data, employee records, internal mappings, personal names, targets, or local file paths are included. All examples are synthetic. Review your organization's privacy, legal, and works-council requirements before using real HR data.

## License

MIT
