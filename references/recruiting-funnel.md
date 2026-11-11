# Recruiting funnel analysis

Use this reference for stage conversion, drop-off, stage aging, time-in-stage, pipeline health, and funnel dashboards.

## Executable workflow

For a CSV with one row per application-stage event, run:

```bash
python3 scripts/analyze_recruiting_funnel.py INPUT.csv \
  --config configs/recruiting-funnel.example.yaml \
  --mapping configs/mappings/canonical-event-history.yaml \
  --output-dir OUTPUT_DIR
```

Use a mapping under `configs/mappings/` as a starting point and adapt it to the actual export. The files use JSON-compatible YAML so the workflow has no third-party dependency. Do not run conversion analysis on a current-status-only export; without stage history it can support backlog and aging only.

The analyzer writes aggregate funnel, outcome, aging, segment, configured-metric, metric-dictionary, quality, summary, and run-manifest outputs. Review `data_quality.csv` before using the metrics. It excludes rows with blank application keys, unmapped stages, or invalid stage-entry timestamps and reports the excluded counts.

## Model the funnel before calculating it

Build a stage map from the user's actual ATS workflow. A common high-level sequence is:

`applied -> screened -> assessed -> interviewed -> offered -> accepted -> started`

Do not force this sequence onto a different process. Preserve raw statuses and map them to canonical stages with explicit rules. Keep terminal outcomes such as `rejected`, `candidate_withdrew`, `offer_declined`, `no_show`, `cancelled`, and `requisition_closed` separate from forward progression.

Use `application_id` or another application-requisition key as the preferred grain. One candidate may apply to multiple requisitions, re-enter a stage, skip stages, or move backward. State how each case is handled.

## Choose the analytical view

Use one or more views, but do not mix their denominators silently:

- **Period activity:** events that occurred during the reporting period. Good for operational workload.
- **Entry cohort:** applications or requisitions that entered the funnel during a defined period, followed through later outcomes. Good for end-to-end yield.
- **Stage-entry cohort:** applications entering a specific stage during a period, followed to the next outcome. Good for stage conversion and SLA.
- **Current snapshot:** active records at an as-of date. Good for backlog and aging.

Exclude immature cohorts from final-outcome rates or label the result as provisional. Report cohort maturity or observation coverage.

## Core funnel metrics

### Stage volume

Count distinct eligible applications entering or present in each stage. Label whether the count represents entries, exits, unique records ever reaching the stage, or current backlog.

### Adjacent-stage conversion

`distinct applications reaching next stage / distinct eligible applications reaching current stage`

Define how skipped stages, direct hires, reopened applications, and duplicate events are treated.

### Cumulative yield

`distinct applications reaching selected outcome / distinct applications entering the funnel cohort`

Examples include application-to-offer, application-to-acceptance, and application-to-start yield. Use mature cohorts for final outcomes.

### Stage drop-off

`eligible applications ending at a stage / eligible applications reaching that stage`

Show employer rejection, candidate withdrawal, administrative closure, and unknown reason separately where possible. Do not calculate drop-off as `1 - conversion` when records can remain active, skip stages, or have other outcomes.

### Time in stage

`stage exit timestamp - stage entry timestamp`

For open records, stage age is `as-of timestamp - stage entry timestamp`. Report median, P75, and aging bands; avoid relying on the mean alone. Define business-calendar handling and paused time.

### End-to-end cycle time

Measure between named events, such as application-to-offer, application-to-acceptance, or application-to-start. Report completed cohorts separately from active records.

### SLA attainment

`eligible stage events completed within threshold / eligible completed stage events`

Name the stage, threshold, owner, calendar, exclusions, and clock-stopping rules.

### Backlog and aging

Count active applications in each stage at the as-of date, split into agreed age bands. Show unknown or stale statuses separately. Backlog is a stock measure and should not be added to period event counts.

## Diagnostic cuts

Useful dimensions include requisition family, business unit, job level, location, source, recruiter, hiring-manager organization, application cohort, and requisition cohort. Start broad, show counts beside rates, and suppress small or sensitive cells.

Compare like-for-like cohorts. Role mix, hiring volume, process design, ownership changes, and observation time can materially affect funnel rates; do not use raw conversion or speed as an individual recruiter ranking.

## Funnel quality checks

- Every stage event has a stable application or application-requisition key.
- Stage timestamps are parseable and sequences are possible.
- Repeated stages and reopened records follow an explicit rule.
- The same application is counted once per metric-defined stage population.
- Active, terminal, and unknown records reconcile to the stage population.
- Skipped stages, direct moves, and missing history are quantified.
- Final-outcome cohorts have enough observation time.
- Funnel totals reconcile to source activity within documented exclusions.

## Recommended outputs

- Funnel table with stage entries, adjacent conversion, cumulative yield, drop-off outcomes, and counts.
- Trend view by stage-entry or application cohort.
- Time-in-stage chart using median, P75, and aging bands.
- Current backlog table by stage and age band.
- Diagnostic cuts for the few dimensions that explain meaningful variation.
- Notes covering stage mapping, cohort basis, maturity, exclusions, and data gaps.

Avoid a decorative funnel chart as the only output: its widths can obscure denominator changes and do not show active or immature records.
