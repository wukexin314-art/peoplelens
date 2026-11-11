# HR metric definitions

Use this reference to select and document defensible formulas. It is an extensible catalog, not an exhaustive or mandatory scorecard. Adapt definitions to the user's policy; never silently replace an established definition.

## Required metric metadata

For each recurring KPI, record: name, business question, grain, metric type, population, event date, window or as-of date, numerator, denominator, exclusions, segments, target source, desired direction, refresh cadence, owner, and known limitations.

For a requested metric not listed here, create a metric contract before calculating it. State whether the result is a count, stock, flow, rate, duration, cohort outcome, index, or currency measure. Do not substitute a nearby standard metric without telling the user.

## Recruiting metrics

For stage-by-stage recruiting analysis, read [recruiting-funnel.md](recruiting-funnel.md).

### Recruiting demand and requisitions

- **Approved openings:** sum approved positions at the target grain; do not count requisition records when one requisition can contain multiple openings.
- **Open requisitions or openings:** active demand as of a date under the organization's status policy.
- **Requisition fill rate:** `filled openings / eligible approved openings` for a defined requisition cohort or period. State whether partially filled requisitions count.
- **Requisition aging:** `as-of date - approved/opened date` for still-open demand. Report median, P75, and aging bands.
- **Vacancy days:** days an approved opening remains unfilled; distinguish current open age from completed time to fill.
- **Backlog:** active applications, interviews, offers, or approvals waiting at an as-of date, segmented by aging band when useful.

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

### Time to hire

`accepted or started date - application date or first active sourcing date`

This is candidate-centered and is not interchangeable with time to fill. State the chosen start and end events.

### Time to start

`actual start date - accepted date`

Separate planned from actual start dates and report no-shows independently.

### Hiring velocity

Count hires, accepted offers, or filled openings per comparable unit of time. Label the event and avoid comparing partial periods without pacing context.

### Candidate and offer outcomes

- **Candidate withdrawal rate:** candidate withdrawals divided by candidates reaching the chosen eligible stage.
- **Offer decline rate:** declined eligible offers divided by eligible offers extended.
- **Offer acceptance-to-start yield:** actual starts divided by accepted offers from a mature cohort.
- **No-show rate:** accepted candidates who do not start divided by mature accepted offers expected to start.
- **Candidate experience score:** use only a defined survey instrument and response population; always show response count and response rate.
- **Recruiting SLA attainment:** eligible events completed within an agreed threshold divided by eligible events. Name the owner and clock-stopping rules.

### Source quality and cost

- **Qualified-source rate:** applications reaching a defined qualification stage divided by eligible applications from that source.
- **Source-to-hire yield:** hires or starts divided by eligible applications from the same source and mature cohort.
- **Quality after hire by source:** an approved aggregate outcome such as 90-day retention by source. Do not create individual quality scores or use performance outcomes without appropriate governance.
- **Cost per hire:** eligible internal and external recruiting costs divided by eligible hires. Document cost scope and allocation rules.
- **Agency dependency:** agency hires or spend divided by the relevant hiring or spend total.

### Recruiter workload or delivery

Counts can be segmented by recruiter, level, business unit, or source, but they are descriptive. Do not rank recruiters without accounting for requisition difficulty, role mix, ownership changes, and exposure time.

## Workforce metrics

### Point-in-time headcount

Count distinct active employees as of the snapshot date under the organization's active-status policy.

### Net headcount change and growth

`closing headcount - opening headcount`; growth rate is `net change / opening headcount`. Reconcile the change to hires, separations, and in-scope transfers.

### Average headcount

Prefer the mean of regular snapshots across the period. If only opening and closing snapshots exist, use `(opening headcount + closing headcount) / 2` and label the approximation.

### Workforce turnover rate

`eligible separations during period / average eligible headcount during period`

State whether the result is monthly, quarterly, annual, or annualized. Separate voluntary and involuntary turnover when supported.

### Internal mobility and promotion

- **Internal mobility rate:** eligible internal moves during the period divided by the chosen eligible employee population or average headcount.
- **Promotion rate:** eligible promotions divided by the eligible employee population. Define what qualifies as a promotion and whether multiple promotions per person are possible.
- **Internal fill rate:** openings filled by internal candidates divided by eligible filled openings.

### Tenure, workforce mix, and capacity

- **Tenure distribution:** active headcount by agreed tenure bands as of a date.
- **Employment mix:** headcount or FTE by employment type, location, level, or organizational unit.
- **FTE:** sum contracted or policy-defined FTE, not employee count.
- **Span of control:** direct reports per people manager; report a distribution rather than only an average.
- **Manager ratio:** people managers divided by eligible headcount under a documented manager definition.

### Absence, engagement, and learning

Calculate these only when the corresponding governed source exists:

- **Absence rate:** eligible absence time divided by scheduled eligible work time.
- **Engagement or pulse score:** follow the survey instrument's scoring rule; show response rate and avoid exposing small teams.
- **Learning completion:** completed required learning assignments divided by eligible assignments or people, depending on policy.
- **Training participation:** distinct eligible participants divided by the eligible population.

### Workforce planning

- **Plan variance:** actual headcount or FTE minus plan, shown as count and percentage where the denominator is meaningful.
- **Hiring plan attainment:** eligible hires or starts divided by planned hires for the same period and population.
- **Forecast gap:** forecast headcount or FTE minus plan at a stated future date.
- **Critical-role coverage:** filled or succession-covered critical positions divided by eligible critical positions, only under an approved role framework.

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

For recruiting, also consider requisition family, hiring manager organization, location, remote/on-site policy, stage, disposition reason, application month, and requisition cohort. For workforce analysis, tenure band, employment spell, manager/non-manager, and movement type may be useful. Treat sensitive or protected attributes as governed fairness/compliance dimensions, not ordinary performance cuts.

When groups have materially different exposure, role mix, or cohort maturity, use rates with denominators and show counts beside them. Avoid league tables based on small counts.

## Rounding and reconciliation

- Calculate with full precision; round only for display.
- Use weighted totals, not averages of displayed subgroup percentages.
- Display `N/A` for a zero denominator.
- Show numerator and denominator with rates where space permits.
- Reconcile grouped counts to the overall eligible population.
