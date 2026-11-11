# HR data contract and reconciliation

Use this reference when inspecting inputs, mapping fields, combining sources, or updating a tracker.

## Identify the grain first

Typical grains are:

- employee event: one hire, transfer, or separation event;
- employee snapshot: one employee per snapshot date;
- candidate or application: one application per candidate-requisition pair;
- offer: one offer event or offer version;
- requisition: one opening or requisition;
- target: one target per period and organizational unit.

Never join two sources until their grains and intended relationship are explicit. A candidate can have multiple applications, offers, or requisitions; an employee can have multiple employment spells.

## Canonical fields

Map only the fields needed for the task. Preserve original columns and document aliases.

| Canonical field | Common aliases | Notes |
|---|---|---|
| `employee_id` | employee ID, worker ID, ERP ID | Preferred key for workforce events |
| `candidate_id` | candidate ID, application ID, sequence ID | Prefer an application-level key when one candidate can apply more than once |
| `requisition_id` | req ID, job ID, opening ID | Stable recruiting key |
| `event_type` | hire/leave type, action, movement type | Normalize to hire, separation, transfer, snapshot |
| `employment_type` | worker type, personnel type | Regular, intern, contractor, etc. |
| `business_unit` | BU, organization, department, delivery team | Keep raw and mapped values |
| `job_level` | level, grade, job grade, level description | Separate level family from exact grade |
| `hire_date` | start date, latest hire date, onboard date | Define whether planned or actual |
| `separation_date` | termination date, leave effective date | Use the effective date unless policy says otherwise |
| `separation_type` | voluntary/involuntary, resignation/termination | Never infer from missing text without labeling the rule |
| `pre_separation_status` | status before leave | Useful for probation attrition |
| `source_of_hire` | source, recruiting source | Normalize to a controlled category list |
| `recruiter` | owner, recruiter name | Personal reporting may require suppression |
| `offer_date` | offer accepted date, acceptance date | State whether issued or accepted date is used |
| `offer_stage` | candidate status, offer status | Normalize with an explicit mapping |
| `requisition_status` | req status, opening status | Keep separate from candidate status |
| `target_headcount` | opening target, hiring target | Store by period and business unit |
| `snapshot_date` | report date, as-of date | Required for point-in-time headcount |

## Normalization rules

- Trim whitespace, normalize case for matching, and preserve the original value.
- Parse Excel serial dates and text dates into one ISO date type. Record parse failures.
- Use mapping tables for business units, grades, channels, and statuses; do not bury business logic in chart labels.
- Keep `Unknown` distinct from `Other`. Unknown means missing or unmapped; Other means a known residual category.
- Treat cancelled, rejected, withdrawn, and declined records according to the metric contract, not with one universal exclusion.

A useful recruiting status model is:

`sourcing -> interview -> offering -> accepted -> waiting_onboard -> onboarded`

Terminal exception states can include `candidate_declined`, `offer_rejected`, `cancelled`, and `requisition_closed`. Preserve the raw state and the rule that produced the normalized state.

## Reconciliation and tracker updates

Use the following precedence:

1. Explicit user-provided source-of-truth rule.
2. Stable system ID plus the most authoritative system.
3. Stable system ID plus the latest reliable effective timestamp.
4. Manual review.

Names are not stable identifiers. If a legacy workflow embeds a sequence ID in a display name, extract and validate the ID, but retain unmatched and duplicate IDs for review.

For every proposed update, capture:

| Field | Meaning |
|---|---|
| `match_key` | Stable ID used to connect records |
| `match_confidence` | exact, rule-based, or manual |
| `field` | Updated canonical field |
| `before` / `after` | Original and proposed values |
| `source` | Authoritative source file or system |
| `rule` | Status/date/mapping rule applied |
| `review_status` | applied, unresolved, or needs review |

Write updates to a copy unless the user explicitly requests an in-place update. Do not update ambiguous matches. Summarize applied, unchanged, unmatched, and conflicting rows.

## Minimum validation

- Key uniqueness at the stated grain.
- Duplicate and blank key counts.
- Missingness for required fields.
- Date range and invalid sequence counts.
- Unknown mapping counts by field.
- Source row count -> eligible row count -> excluded row count reconciliation.
- Before/after row and key counts for any merge.
