# Recruiting funnel example

This synthetic example demonstrates the executable first phase of PeopleLens. It contains no real people, company, requisition, or hiring data.

Run from the repository root:

```bash
python3 scripts/analyze_recruiting_funnel.py \
  examples/recruiting-funnel/applications.csv \
  --config configs/recruiting-funnel.example.yaml \
  --mapping configs/mappings/canonical-event-history.yaml \
  --output-dir examples/recruiting-funnel/output \
  --force
```

The input grain is one row per application-stage event. The committed output shows the expected artifact set:

- `funnel_summary.csv`: stage volume, adjacent conversion, cumulative yield, terminal drop-off, backlog, median duration, and P75 duration;
- `stage_outcomes.csv`: terminal outcomes by stage;
- `backlog_aging.csv`: current active pipeline by stage and aging band;
- `segment_summary.csv`: application-to-start yield by configured segments;
- `configured_metrics.csv`: metrics declared in the YAML configuration;
- `metric_dictionary.csv`: generated definitions for configured metrics;
- `data_quality.csv`: structural and sequence checks without candidate-level values;
- `analysis_summary.md`: compact decision-oriented summary;
- `run_manifest.json`: input counts, stage order, as-of date, and generated files.

Rates are decimals so downstream spreadsheets and BI tools can format them without parsing percentage strings.
