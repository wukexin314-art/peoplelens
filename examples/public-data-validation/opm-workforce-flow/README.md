# OPM workforce-flow validation

This validation uses the August 2026, version 1 accessions and separations files from the official [OPM FWD API](https://data.opm.gov/get-data/api-access). The files are public government data and contain no direct personal identifiers. Raw Parquet files are intentionally not committed.

## Download the pinned files

```bash
curl -fsSL "https://data.opm.gov/api/v1/files/accessions/2026/08/1/download" \
  -o /tmp/accessions_202608_1.parquet
curl -fsSL "https://data.opm.gov/api/v1/files/separations/2026/08/1/download" \
  -o /tmp/separations_202608_1.parquet
```

Expected SHA-256 checksums at the time of validation:

```text
c8f5f55edcc26234615c4215243d5a67bfa1c21024e9260b60057b1a48f85bca  accessions_202608_1.parquet
68a4149570f9c34227ab4a3f13362be793e70f732b7d0ef60bcaced2b7e50a94  separations_202608_1.parquet
```

If OPM republishes the same version with different bytes, inspect its release notes before updating the expected outputs.

## Run

From the repository root:

```bash
python3 -m pip install -r requirements-parquet.txt
python3 scripts/profile_hr_data.py /tmp/accessions_202608_1.parquet \
  --output /tmp/opm-accessions-profile.json
python3 scripts/analyze_opm_workforce_flow.py \
  --accessions /tmp/accessions_202608_1.parquet \
  --separations /tmp/separations_202608_1.parquet \
  --start-month 2026-08 \
  --end-month 2026-08 \
  --group-by department \
  --output-dir /tmp/peoplelens-opm-202608
```

The source files contain late-reported actions with effective months before August. The reference run therefore excludes 3,718 rows outside the requested effective-month window. The expected aggregate is 18,566 accessions, 10,548 separations, and net personnel-action flow of +8,018. This is not a headcount-growth or turnover measure.

Compare the stable aggregate files in [`expected`](expected). The run manifest is not committed because its generation timestamp and local filenames are execution-specific.
