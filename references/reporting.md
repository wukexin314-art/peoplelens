# HR reporting and dashboard playbook

Use this reference for recurring reports, dashboards, charts, tables, and written findings.

## Build the report around decisions

Each page or section should answer one question:

- What changed?
- Where is the change concentrated?
- Is it above or below an agreed target or prior period?
- Is the pattern reliable enough to act on?
- What validation or operational action should happen next?

Do not turn every available field into a chart. Prefer a small set of traceable KPIs and diagnostic cuts.

## Recommended structure

1. Scope line: reporting window, as-of date, population, and sources.
2. Executive summary: 3-5 findings with magnitude and context.
3. KPI scorecard: current value, comparison, delta, numerator/denominator, and status.
4. Diagnostic views: trends, segments, and cohort maturity.
5. Operational detail: unresolved records, backlog, or change log where appropriate.
6. Methodology and data-quality notes.

## Chart selection

- Time trend: line chart with a consistent date axis and visible zeroes for missing periods only when zero is true.
- Actual vs target: bullet chart or horizontal bars; show actual, target, and time-progress marker.
- Source or level mix: bars or 100% stacked bars, with counts available.
- Retention or early attrition: cohort table, survival-style curve, or rates with mature cohort counts.
- Voluntary vs involuntary separation: stacked bars with total rate and counts.
- Detail/reconciliation: table with filters, not a dense chart.

Avoid pie charts for many categories, dual axes with unrelated scales, and red/green as the only status cue.

## Findings language

A strong finding includes:

`metric + direction + magnitude + location/cohort + comparison + caveat`

Example pattern: “Early attrition rose 2.1 percentage points quarter over quarter, concentrated in the Operations P1-P4 cohort; the latest cohort is only 78% mature, so treat the movement as directional.”

Use causal language only when the analysis supports causality. Otherwise use “associated with,” “concentrated in,” or “consistent with,” and name the next validation step.

## Status and targets

- Label the source of every target.
- Use neutral labels such as on track, watch, and off track.
- Separate outcome status from data-quality status.
- Never manufacture a benchmark from the observed data.
- Time-progress markers are context, not a performance verdict.

## Recurring automation

For monthly or quarterly refreshes:

1. Parameterize the reporting window, as-of date, source paths, targets, mappings, and exclusions.
2. Keep metric logic separate from styling.
3. Save a machine-readable metric table before producing charts.
4. Produce a run log with input versions, row counts, exclusions, warnings, and output paths.
5. Fail closed on missing required columns or ambiguous joins.
6. Compare the new run with the previous run and flag unexplained discontinuities.

Do not install dependencies, overwrite source workbooks, or publish reports as a hidden side effect of analysis.

## Output QA

- Titles state the metric and period.
- Axes, units, and denominator are visible.
- Tables sort in a meaningful business order.
- Grand totals use weighted calculations.
- Filters and exclusions match across pages.
- Exported Excel, PDF, image, or HTML output is opened or rendered and visually checked.
- No personal data appears in a public or broadly shared artifact.
