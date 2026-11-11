# Privacy and responsible people analytics

Use this reference whenever data is row-level, contains identifiers or sensitive attributes, uses small cohorts, or will be shared outside the immediate working group.

## Minimize and protect

- Use only fields necessary for the stated analysis.
- Prefer local processing when practical and do not upload HR data to an external service without authorization.
- Do not include raw names, emails, phone numbers, addresses, government IDs, free-text notes, or exact birth dates in prompts, logs, examples, screenshots, or public repositories.
- Use stable pseudonymous IDs for joins; keep any re-identification key outside the analysis output.
- Do not copy real employee or candidate rows into test fixtures. Create synthetic examples.

## Aggregation and small cells

Use the organization's policy when provided. Otherwise use a conservative default minimum cell size of 5 and disclose it. Suppress or combine small groups, and ensure hidden values cannot be derived by subtracting visible subtotals from totals.

For rates, consider suppressing both numerator and denominator when either reveals a small cell. A small-cell threshold is not a guarantee of anonymity; rare combinations can still identify people.

## Sensitive and protected attributes

Analyze attributes such as age, disability, ethnicity, gender, nationality, race, religion, sexual orientation, pregnancy, or family status only for a legitimate aggregate fairness, compliance, or inclusion purpose and within the user's policy and jurisdiction. Never infer these attributes from names, photos, text, or location.

Do not use protected or proxy attributes to rank individuals or recommend hiring, firing, promotion, pay, discipline, scheduling, or other employment decisions.

## Free text

Exit reasons, manager notes, interview feedback, and employee comments can contain sensitive or identifying content. Summarize themes only after redaction and aggregation. Do not quote distinctive text without explicit authorization and a clear need.

## Publishing checklist

Before sharing outside the organization:

- remove company names, internal paths, usernames, targets, org mappings, and employee or recruiter names;
- replace real data with synthetic fixtures;
- scan repository history and generated files, not just current source files;
- remove screenshots or exports that contain hidden workbook tabs, comments, metadata, or personal data;
- document that examples are synthetic;
- confirm that suppression and rounding do not permit reconstruction.

## Decision boundary

The skill may describe aggregate patterns, data quality, process friction, and workforce risks. It must not make or automate a high-impact decision about a person. When a user asks for such a recommendation, redirect to an aggregate, policy-based, human-reviewed analysis.
