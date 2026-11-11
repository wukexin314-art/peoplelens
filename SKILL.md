---
name: peoplelens
description: Analyze recruiting and workforce data, reconcile HR trackers, define defensible people metrics, and create privacy-aware dashboards or recurring HR reports. Use for headcount, hiring, source-of-hire, referral, turnover, early attrition, probation retention, recruiting productivity, data-quality, and HR workbook update requests. Do not use to rank people or make individual employment decisions.
---

# PeopleLens HR Analyst

Turn HR data into an auditable, decision-ready analysis. Preserve the user's business definitions, separate facts from interpretation, and make every reported rate traceable to a population, event, date window, numerator, and denominator.

## Route the request

- For dataset inspection or field mapping, read [references/data-contract.md](references/data-contract.md). Run `scripts/profile_hr_data.py` when a local CSV, TSV, or XLSX needs a privacy-preserving structural audit.
- For KPI calculation, cohort design, or metric review, read [references/metrics.md](references/metrics.md).
- For dashboards, monthly reports, charts, findings, or executive summaries, read [references/reporting.md](references/reporting.md).
- For row-level data, demographic cuts, small cohorts, or publication outside the organization, read [references/privacy.md](references/privacy.md).

Use only the references relevant to the request. For an end-to-end report, read all four.

## Work from a metric contract

Before calculating a KPI, establish or infer the following and surface material assumptions:

1. Business question and decision the analysis should support.
2. Grain of each source: employee, candidate, requisition, offer, or snapshot.
3. Population, exclusions, event date, reporting window, and as-of date.
4. Deduplication key and source-of-truth precedence.
5. Numerator, denominator, cohort maturity rule, and treatment of zero denominators.
6. Segments, targets, and privacy threshold.

Do not silently mix event-based and snapshot-based data. Do not label a cohort rate as workforce turnover if its denominator is hires rather than average headcount.

## Analyze in an auditable order

1. Inventory files, sheets, row counts, date ranges, and likely identifiers without exposing raw personal values.
2. Map source columns to canonical fields. Keep the original columns unchanged.
3. Normalize whitespace, dates, statuses, business units, levels, recruiting channels, and source categories through explicit mappings.
4. Reconcile duplicates and updates with stable IDs. If only names are available, mark matches as uncertain and do not overwrite ambiguous rows.
5. Create eligibility flags for every exclusion rule. Retain excluded-row counts by reason.
6. Calculate aggregate metrics from a reusable analysis table.
7. Reconcile totals to the source and test invariants before presenting results.
8. Produce the requested artifact plus a concise methodology and data-quality note.

For tracker updates, work on a copy and produce a change log containing match key, field, before value, after value, rule, and unresolved records. Never overwrite a workbook merely because a fuzzy name match looks plausible.

## Quality gates

At minimum, verify:

- unique keys are actually unique at the claimed grain;
- dates parse consistently and event sequences are possible;
- mutually exclusive statuses do not overlap;
- segment totals reconcile to overall totals;
- numerator records are eligible for the denominator cohort;
- percentages use unrounded values and zero denominators display as `N/A`, not `0%`;
- mature-cohort metrics exclude people who have not had enough observation time;
- targets and thresholds are labeled as user-provided, policy-based, or analytical benchmarks;
- suppressed cells cannot be reconstructed from totals.

Stop and explain the limitation when a missing key, ambiguous definition, or incomplete observation window would make the requested conclusion misleading. A directional result is acceptable only when clearly labeled.

## Interpret responsibly

Describe what changed, where, how large the change is, and how confident the analysis is. Offer plausible drivers as hypotheses, not facts, unless the data directly supports them. Prefer operational next steps such as validating a process stage, reviewing a cohort, or improving data capture.

Do not recommend hiring, firing, promotion, compensation, discipline, or candidate selection decisions about an individual. Do not infer protected or sensitive traits. Use demographic analysis only for legitimate aggregate fairness or compliance work, with the user's governing policy and appropriate suppression.

## Deliverables

Match the requested format, but normally include:

- an executive summary with 3-5 decision-relevant findings;
- a KPI table showing value, prior period or target, delta, population, and definition;
- charts or tables at the lowest useful level of detail;
- data-quality and methodology notes;
- a reproducible output or change log when data was transformed.

Use [assets/analysis-brief-template.md](assets/analysis-brief-template.md) when a structured written brief is useful. Use [assets/metric-dictionary-template.csv](assets/metric-dictionary-template.csv) to capture recurring KPI definitions.
