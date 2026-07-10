# D6 MVP Changelog

## Current Pass

- Added a pure `src/sez_calibration/calibration_model.py` module for synthetic D6 calibration calculations.
- Added synthetic D6 assumption, enterprise-weight, and verification-rule inputs under `data/synthetic/`.
- Expanded the pipeline to generate D6 CSV outputs and an Excel review workbook with assumptions, scenarios, annual enterprise outputs, portfolio aggregation, sensitivity, parameter ranges, readiness triage, reconciliation, validation flags, and D7 handoff.
- Updated activity classification from `operating_productive` to `reported_operating_activity` while keeping backward-compatible interpretation in the engine.
- Refocused the default Streamlit navigation to:
  - Calibration Analysis
  - Readiness Triage
  - Case Calibration
  - Evidence & Exports
  - About / Limitations
- Added a D6-first Calibration Analysis page with 2026-2035 scenario outputs, deduction/carryforward trace, revenue-neutral parameter ranges, verification requirements, and D7 handoff.
- Added Case Calibration view for one-zone/one-enterprise review, including gate-cleared vs blocked calibration status.
- Added D6 regression tests for deduction formulas, customs annualization, revenue-neutral solver status, generated CSVs, and workbook sheet coverage.
- Expanded the synthetic data dictionary with units, currency, period, annual/cumulative/stock status, source level, missingness rule, and model use.

## Guardrails Preserved

- Public/default app remains a synthetic demo view.
- No final legal, fiscal, tax, or incentive decisions are made.
- Legal fields remain subject to D4 review.
- Fiscal/FBR fields remain subject to D5/FBR/customs validation.
- Support-related outputs remain provisional and subject to validation.
- No pilot zone is selected by the D6 model.
- Scenario Settings remains hidden unless `SHOW_ADVANCED_SCENARIOS=1`.
