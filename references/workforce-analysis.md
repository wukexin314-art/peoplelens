# Workforce analysis

Use the workforce analyzer for a CSV with one row per employment spell. A rehire should be a new row with the same employee ID and a new hire date.

```bash
python3 scripts/analyze_workforce.py INPUT.csv \
  --config configs/workforce.example.yaml \
  --output-dir OUTPUT_DIR
```

The analyzer calculates opening and closing headcount, period hires and separations, net change, headcount growth, approximate turnover, closing FTE, separation mix, and mature-cohort early attrition and retention. It produces aggregate-only segment results with small-cell and complementary suppression.

Opening headcount is measured on the day before `period_start`; closing headcount is measured on `period_end`. Turnover uses period separations divided by `(opening headcount + closing headcount) / 2` and labels that denominator as an approximation. Use regular snapshots instead when available.

The input must contain stable employee IDs and hire dates. Optional fields include separation date, separation type, FTE, and configured segments. The analyzer does not reconstruct effective-dated transfers from a single employment-spell row, so segment turnover is descriptive of the stored segment value. Do not interpret it as historical organizational attribution when employees moved during the period.

For an N-day early attrition or retention rate, the denominator contains period hires whose full N-day observation window has elapsed by `as_of_date`. A separation on or before the N-day milestone counts as early attrition.
