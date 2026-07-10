# SEZ D6 Calibration Workbench

Executable synthetic proof of concept for D6 calibration architecture, fiscal-envelope testing, and D7 pilot handoff.

This repository is scoped to a demoable Pakistan SEZ D6 calibration MVP. It uses synthetic zone and enterprise records by default. It does not approve incentives, set final tax rates, determine final validated fiscal cost, select a pilot zone, or replace BOI, FBR, Finance Division, SEZA, Law Division, IMF, programme, fiscal modeller, legal counsel, or human review.

## Demo Flow

`synthetic enterprise archetype -> model-readiness status -> D5 fiscal envelope -> joint package/rate/cap/threshold/utilization/uptake controls -> current envelope decision -> nearest feasible tested configuration -> additionality sensitivity -> verification requirements -> D7 recalibration triggers -> export`

The controlled decision question is:

> Is the currently selected temporary cost-based incentive configuration within the illustrative D5 fiscal envelope, and if not, what is the nearest feasible tested joint configuration? What evidence, verification conditions, and D7 recalibration rules must be satisfied before proceeding?

## How To Run

```bash
pip install -r requirements.txt
python run_demo.py
streamlit run app.py
```

The app opens to **Calibration Analysis** in **Synthetic demo view**.

## What Changed In This Pass

- Corrected scenario definitions so status quo, accelerated removal, cost-based regime, combined transition/pilot, and no-SEZ reference have distinct policy meaning.
- Separated `evidence_model_ready` from `support_eligibility_status` and `transition_treatment_status`.
- Removed hidden reduced-CIT phase-in from the cost-based scenario.
- Made additionality scenario-relative: the no-SEZ reference receives no incentive-caused incremental income.
- Added threshold semantics: `qualifying_expenditure_threshold_pkr_m` is a minimum annual claim threshold.
- Added transparent fiscal identities: benchmark tax liability, tax collected, tax expenditure, cash net revenue, and fiscal impact versus reference.
- Replaced the old ceiling-search language with a tested joint-configuration frontier against an illustrative D5 fiscal envelope.
- Made incentive-caused incremental income conditional on a positive available incentive after package, rate, threshold, cap, and utilization settings.
- Scaled frontier fiscal cost, incremental income, administrative cost, workload, and annual FTE consistently by pilot uptake.
- Added administrative workload and cost calculations from claim count, review hours, audit sample rate, and cost per review hour.
- Added operational D7 recalibration triggers.

## Data

The default demo uses synthetic files in `data/synthetic/`. These are hypothetical zones and enterprises only. They are not BOI, SEZA, FBR, Finance, legal, developer, or enterprise records.

The older source-derived structured screening dataset covers 35 detected zone profile records and 35 indicator records based on the source digest. It is retained for internal/reference use only. Exact row-level verification for any source-derived use should rely on the original workbook and source documents before policy use.

## Real-Use Inputs Needed

- BOI/SEZA zone master, plot-level, and enterprise records.
- D4 legal classifications, development agreements, sunset clauses, and grandfathering/transition constraints.
- D5/FBR/Finance fiscal exposure data, tax paid, customs exemptions, incentive utilization, and fiscal-cost assumptions.
- Enterprise-level production, construction, employment, exports, investment, CAPEX, R&D, training, and compliance evidence.
- KPI assurance inputs, verification evidence, audit triggers, and monitoring data.
- Additionality, counterfactual, displacement, and net fiscal/economic impact analysis.

## Outputs

The pipeline writes CSV/JSON/XLSX outputs to `outputs/`, including:

- `calibration_enterprise_inputs.csv`
- `calibration_model_readiness.csv`
- `calibration_annual_enterprise.csv`
- `calibration_portfolio_summary.csv`
- `calibration_sensitivity.csv`
- `calibration_parameter_ranges.csv`
- `calibration_verification_rules.csv`
- `calibration_d7_handoff.csv`
- `sez_calibration_demo_outputs.xlsx`

The Excel workbook includes assumptions, scenario definitions, annual enterprise outputs, portfolio summary, tested joint-configuration frontier, sensitivity, verification rules, readiness triage, reconciliation, validation flags, D7 handoff, reason codes, and limitations.

## Demo Script

1. Open **Calibration Analysis** and state the decision question.
2. Select the instrument package and show the illustrative D5 fiscal ceiling.
3. Adjust CAPEX rate, annual cap, threshold, utilization, or pilot uptake.
4. Show whether the current joint configuration is inside or outside the envelope.
5. Point to the nearest feasible tested joint configuration and then open the frontier table.
6. Show low/base/high additionality sensitivity.
7. Open verification requirements and D7 recalibration triggers.
8. Use **Case Calibration** and **Evidence & Exports** only as supporting evidence pages.
9. Close with **About / Limitations**: synthetic proof of concept, human review required, D4/D5 validation required, no final policy decision.

## Documentation

- `docs/D6_MODEL_METHOD.md`
- `docs/ECONOMIC_COHERENCE_CHECKS.md`
- `docs/DEMO_DECISION_TRACE.md`
- `docs/HOW_TO_DEMO.md`
- `LIMITATIONS.md`
- `D6_MVP_CHANGELOG.md`
