# HR metric definitions

Use this reference to select and document defensible formulas. Adapt the definitions to the user's policy; never silently replace an established definition.

## Required metric metadata

For each recurring KPI, record: name, business question, grain, population, event date, window, numerator, denominator, exclusions, segments, target source, refresh cadence, owner, and known limitations.

## Recruiting metrics

### Valid accepted offers

Count distinct eligible offer or application IDs whose acceptance event falls in the period. Exclude cancelled, rejected, rescinded, or candidate-declined records only when the business definition calls for it. State whether the date is offer issued, offer accepted, or planned start.

### Hiring completion

`accepted offers or onboarded hires / approved opening target`

Use the event that matches the target policy. Keep actual completion above 100% if it occurs; a chart may cap its visual scale but not the reported value.

### Expected time progress

`elapsed days in target period / total days in target period`

Use calendar or business days consistently. This is a pacing reference, not proof that hiring should progress linearly.

### Offer acceptance rate

`accepted offers / eligible offers extended`

Define how withdrawn, expired, revised, and duplicate offers are handled.

### Referral share

`valid referral outcomes / all valid outcomes in the same population`

The outcome may be accepted offer or onboarded hire. Use the same date event and exclusions in both numerator and denominator. If campus hiring is excluded, exclude it from both.

### Source mix

`valid outcomes from source category / all valid outcomes in scope`

Report unknown sources separately so data-quality problems are visible.

### Time to fill

`requisition filled date - requisition opened or approved date`

Report median and a percentile such as P75; the mean alone is vulnerable to long-tail outliers.

### Recruiter workload or delivery

Counts can be segmented by recruiter, level, business unit, or source, but they are descriptive. Do not rank recruiters without accounting for requisition difficulty, role mix, ownership changes, and exposure time.

## Workforce metrics

### Point-in-time headcount

Count distinct active employees as of the snapshot date under the organization's active-status policy.

### Average headcount

Prefer the mean of regular snapshots across the period. If only opening and closing snapshots exist, use `(opening headcount + closing headcount) / 2` and label the approximation.

### Workforce turnover rate

`eligible separations during period / average eligible headcount during period`

State whether the result is monthly, quarterly, annual, or annualized. Separate voluntary and involuntary turnover when supported.

### Early attrition rate

`cohort hires separating within N days / mature eligible hires in cohort`

For a 60-day rate, include in the denominator only hires with 60 days of observation by the as-of date, unless they already separated within 60 days. State whether day 0, no-shows, interns, transfers, and rehires are included.

### Cohort retention rate

`cohort members retained at milestone / mature eligible cohort members`

This is usually clearer than `1 - attrition` when transfers, data gaps, or competing events exist. Define retained status at the milestone.

### Probation attrition or retention

Use explicit probation status or policy dates. A common attrition form is `probation separations / mature probation cohort`; retention is `retained through probation / mature probation cohort`. Do not mix all hires in the denominator with only probation-coded separations unless that is the documented policy.

## Cohorts and time

- Use an as-of date and freeze it in the output.
- Separate period events from hire cohorts.
- Require sufficient observation time for milestone metrics.
- Keep rehires as separate employment spells unless policy says otherwise.
- Do not compare partial and complete periods without an explicit pacing or prior-period rule.

## Segmentation

Useful dimensions include business unit, geography, level family, exact grade, employment type, recruitment channel, source of hire, recruiter, and cohort month. Start broad and drill down only when sample size and business relevance justify it.

When groups have materially different exposure, role mix, or cohort maturity, use rates with denominators and show counts beside them. Avoid league tables based on small counts.

## Rounding and reconciliation

- Calculate with full precision; round only for display.
- Use weighted totals, not averages of displayed subgroup percentages.
- Display `N/A` for a zero denominator.
- Show numerator and denominator with rates where space permits.
- Reconcile grouped counts to the overall eligible population.
