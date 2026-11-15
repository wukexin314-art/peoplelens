# Workforce flow and OPM FWD

Use this reference for accessions, separations, and net personnel-action flow, especially with the U.S. Office of Personnel Management Federal Workforce Data (FWD) monthly Parquet files.

## OPM file semantics

- FWD accessions and separations files contain personnel-action records and a string-typed `count` field. Sum `count`; do not assume every row always represents one action.
- Use `personnel_action_effective_date_yyyymm` for the analysis period. A file published for one month can contain late-reported actions effective in earlier months.
- Pin year, month, and version in reproducible work. Record the source filenames and effective-month filter in the run manifest.
- Accessions include new hires and transfer-ins. Separations include quits, retirements, terminations, transfer-outs, and other categories. Keep category mix visible before combining them.
- Net personnel-action flow is `accessions - separations`. It is not point-in-time headcount change because transfers, corrections, reorganizations, and other status changes may not reconcile to two event files alone.
- Turnover requires eligible separations divided by compatible average headcount. Do not calculate it from accessions and separations alone.

## Executable workflow

Install the optional Parquet dependency, then run:

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

Review `data_quality.csv` before using the results. `outside_period` is expected when a monthly delivery contains late-reported actions from earlier effective months. Segment results use a minimum cell size of 5 by default and apply complementary suppression when only one small group would otherwise be recoverable.

## Interpretation

Report the largest action categories and the departments contributing most to flow, but describe drivers as hypotheses. A positive net action flow does not prove workforce growth, and a high quit count does not prove a retention problem without exposure, headcount, workforce mix, and a comparable period.
