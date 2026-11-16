# Workforce example

This synthetic employment-spell dataset contains no real people or employer data.

Run from the repository root:

```bash
python3 scripts/peoplelens.py workforce \
  examples/workforce/employee-spells.csv \
  --config configs/workforce.example.yaml \
  --output-dir examples/workforce/output \
  --force

python3 scripts/peoplelens.py report examples/workforce/output \
  --output examples/workforce/report.html \
  --title "Synthetic workforce overview" \
  --force
```

The example demonstrates opening and closing headcount, hires, separations, approximate turnover, FTE, separation mix, segment suppression, and mature-cohort 60-day attrition and retention. Rates are decimals for downstream formatting.
