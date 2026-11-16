# PeopleLens

A privacy-aware Codex skill for recruiting and workforce analytics.

[简体中文](README.zh-CN.md)

It turns recurring HR workflows into a consistent analysis method: inspect data, define metrics before calculating them, analyze hiring and workforce outcomes, and produce decision-ready aggregate reports with an audit trail.

## What is executable today

- Structural profiling for CSV, TSV, XLSX, and Parquet without printing raw values
- Cohort-safe recruiting funnel conversion, drop-off, duration, aging, backlog, and segments
- Employment-spell headcount, hires, separations, growth, approximate turnover, FTE, and N-day retention
- OPM accessions, separations, category mix, and net personnel-action flow
- Greenhouse Analytics stage-change CSV normalization
- Self-contained HTML reports, metric dictionaries, quality checks, privacy suppression, and run manifests

The skill also provides governed methods for requisitions, hiring plans, mobility, promotions, workbook reconciliation, and recurring reports. Those workflows are guided analyses rather than dedicated executable modules; their result depends on the supplied data and the user's business definitions.

The skill is designed for aggregate analysis. It does **not** rank candidates or employees and does not make individual employment decisions.

## Use

Place this folder in a location your Codex setup uses for skills, then invoke `$peoplelens` with a request such as:

- “Audit these HR workbooks and propose a canonical data model.”
- “Calculate 60-day attrition by business unit using mature cohorts.”
- “Analyze application-to-start funnel conversion, drop-off, and time in stage by hiring cohort.”
- “Reconcile this ATS export with the headcount tracker and create a change log.”
- “Build a monthly hiring and retention report with definitions and QA notes.”

The skill can also be selected automatically for relevant HR analytics requests.

Use the unified command-line entry point for deterministic workflows:

```bash
python3 scripts/peoplelens.py --help
```

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

## Executable workforce analysis

For one row per employment spell, calculate opening and closing headcount, period hires and separations, headcount growth, approximate turnover, closing FTE, separation mix, and mature-cohort early attrition and retention:

```bash
python3 scripts/peoplelens.py workforce \
  examples/workforce/employee-spells.csv \
  --config configs/workforce.example.yaml \
  --output-dir /tmp/peoplelens-workforce
```

See the [synthetic workforce example](examples/workforce/README.md). The analyzer treats a rehire as a new employment spell and clearly labels the opening/closing average-headcount approximation.

## Greenhouse adapter and HTML report

Greenhouse Analytics exports based on the **Application stage changes** subject can be normalized to PeopleLens event history before funnel analysis:

```bash
python3 scripts/peoplelens.py adapt-greenhouse greenhouse-stage-changes.csv \
  --output canonical-stage-events.csv
```

Stage names remain raw and must be mapped to the organization's actual interview plan. Current-pipeline snapshots are intentionally not accepted as a substitute for stage history.

The normalized CSV remains row-level recruiting data and can contain application IDs, recruiter names, and other internal fields. Keep it in an approved local location and publish only aggregate outputs.

Render any recruiting-funnel or workforce output directory as a self-contained aggregate HTML report:

```bash
python3 scripts/peoplelens.py report /tmp/peoplelens-workforce \
  --output /tmp/peoplelens-workforce.html
```

## Repository structure

```text
.
|-- SKILL.md
|-- agents/openai.yaml
|-- scripts/
|   |-- peoplelens.py
|   |-- profile_hr_data.py
|   |-- adapt_greenhouse.py
|   |-- analyze_recruiting_funnel.py
|   |-- analyze_workforce.py
|   |-- analyze_opm_workforce_flow.py
|   `-- render_report.py
|-- configs/
|   |-- recruiting-funnel.example.yaml
|   `-- mappings/
|-- examples/
|   |-- recruiting-funnel/
|   |-- workforce/
|   `-- public-data-validation/
|-- references/
|   |-- data-contract.md
|   |-- metrics.md
|   |-- recruiting-funnel.md
|   |-- workforce-analysis.md
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
