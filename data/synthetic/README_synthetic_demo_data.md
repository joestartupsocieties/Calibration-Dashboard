# Synthetic SEZ Demo Data Package

Created: 2026-07-08T18:59:53.935241+00:00

This package is fully synthetic and uses hypothetical zones only. It is designed for a public/demo version of the SEZ Incentive Transition Triage app. It includes the data that is missing or placeholder-only in the current 35-zone source dataset, especially D4 legal status, D5/FBR fiscal exposure bands, additionality/counterfactual/effectiveness flags, KPI and pilot-readiness fields, and enterprise-level summaries.

## Drop-in files for the current app

Copy these files into the app's `data/` directory:

- `SEZ_Key_Indicators_Normalized.csv`
- `legal_fiscal_placeholders.csv`

Then run:

```bash
python run_demo.py
streamlit run app.py
```

## Supporting files

- `synthetic_enterprise_summary.csv` gives one synthetic anchor-enterprise summary per zone.
- `synthetic_data_dictionary.csv` explains the key fields.

## Why this works better for the MVP demo

The current real/source-derived dataset has many fields that are intentionally pending D4 legal review, D5/FBR fiscal verification, enterprise-level source validation, additionality/counterfactual work, and pilot-readiness assessment. This synthetic package fills those fields so the demo can show meaningful provisional pathways rather than only placeholder-driven warnings.

## Built-in case types

- clean productive / high additionality / validated fiscal exposure
- productive / moderate additionality / low fiscal exposure
- productive but additionality not established
- good operating zone but legal hard gate
- high fiscal exposure / low additionality
- construction-stage transition case
- infrastructure constraint / transition review
- allotted but inactive / speculative risk
- vacant/speculative / no support
- non-compliance hard gate
- low confidence / data gap
- productive but missing fiscal exposure file
- export-heavy EPZ comparator
- early-stage / not ready for calibration

## Non-decision statement

These records are not real SEZ records and must not be used for policy analysis. Outputs are provisional demonstration outputs only. They do not approve incentives, set tax rates, determine fiscal cost, or replace BOI, FBR, Finance, SEZA, legal, IMF, programme, or human review.
