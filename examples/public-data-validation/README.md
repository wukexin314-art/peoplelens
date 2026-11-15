# Public-data validation

This directory records external datasets used to validate PeopleLens without committing personal or employer data.

| Dataset | Purpose | Redistribution decision |
|---|---|---|
| [OPM Federal Workforce Data](https://data.opm.gov/get-data/api-access) | Parquet profiling, effective-month filtering, accessions, separations, categories, and department suppression | Versioned expected aggregate outputs are committed; raw Parquet files are not |
| [Job Application Tracker demo](https://github.com/waddington/job-application-tracker) | Recruiting stage mapping, cohort conversion, duration, backlog, and small-cell suppression | Apache-2.0 synthetic demo; source repository remains the canonical copy |
| [IBM HR Analytics synthetic data provenance](https://github.com/netsatsawat/HR-Analytics/blob/master/data/SOURCE.md) | Structural profiling and sensitive-column detection | Raw CSV is not committed because the repository license does not grant rights to IBM's dataset |

The OPM case is the fully reproducible reference run. Other datasets are validation inputs, not benchmarks about real employee behavior. Never interpret synthetic relationships as workforce findings.

See [opm-workforce-flow](opm-workforce-flow/README.md) for exact download URLs, checksums, commands, and expected aggregates.
