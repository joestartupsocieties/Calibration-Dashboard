# SEZ Incentive Transition Triage

Provisional decision-support for legal, fiscal, source-data confidence, and pilot-readiness review.

This repository is scoped to a demoable D6 calibration-analysis flow using fully synthetic hypothetical-zone and enterprise records by default. It does not make final legal, fiscal, tax, or incentive decisions, does not set final tax rates, determine fiscal cost, or replace BOI, FBR, Finance Division, SEZA, Law Division, IMF, programme, fiscal modeller, legal counsel, or human review.

## Demo Flow

`structured screening dataset -> validation flags -> source-data confidence -> readiness gates -> enterprise calibration inputs -> 2026-2035 scenario outputs -> revenue-neutral parameter ranges -> D7 handoff -> export`

Hard guardrails:

- Prototype only.
- Outputs are provisional and subject to validation.
- Human review is required.
- Any support-related output remains subject to D4 legal review and D5/FBR fiscal verification.
- Any cost-based support is temporary transition support only; all SEZ fiscal incentives phase out by 30 June 2035.
- The default public demo uses fully synthetic hypothetical zones and enterprises.
- Legal fields remain placeholders pending D4 legal review.
- Fiscal/FBR fields remain placeholders pending D5/FBR/customs verification.
- No pilot zone is selected by the model.

## How To Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the data pipeline:

```bash
python run_demo.py
```

Run the Streamlit app:

```bash
streamlit run app.py
```

The app opens to **Calibration Analysis** in **Synthetic demo view** for a 3-5 minute walkthrough.

To run the default public synthetic demo:

```bash
python run_demo.py
streamlit run app.py
```

To use source-derived/internal data, set the profile explicitly in an authorized/internal environment only:

```bash
set SEZ_DATA_PROFILE=source
python run_demo.py
streamlit run app.py
```

On macOS/Linux shells, use `export SEZ_DATA_PROFILE=source` instead.

## Demo And Source Data

The default demo uses synthetic files in `data/synthetic/`. These files contain hypothetical zones and enterprises only, including synthetic D4 legal status, D5/FBR fiscal exposure bands, additionality/counterfactual/effectiveness flags, KPI and pilot-readiness fields, enterprise-level summaries, D6 assumptions, aggregation weights, and verification requirements.

The older source-derived structured screening dataset covers 35 detected zone profile records and 35 indicator records based on the source digest. It is retained for internal/reference use, but it is not the default public demo profile.

Exact row-level verification for any source-derived/internal use should use the original workbook and source documents before policy use. The prototype preserves uncertainty, missing fields, source-scope mismatch, cross-source/status conflicts, and validation flags instead of treating any dataset as complete.

If `data/synthetic/SEZ_Key_Indicators_Normalized.csv` is missing, the pipeline creates a clearly marked fallback demo dataset and records a warning in the run metadata. It does not silently switch to source-derived data.

## Data Needed For Real Use

Real policy use requires validated source inputs, including:

- BOI/SEZA zone master and plot-level records.
- D4 legal classifications, development agreements, enterprise certificates, sunset clauses, and grandfathering or transition issues.
- D5/FBR/Finance fiscal exposure data, tax paid, customs exemptions, incentive utilization, and fiscal-cost assumptions.
- Enterprise-level evidence on production, construction, employment, exports, investment, CAPEX, and compliance.
- Infrastructure and utility status from SEZA, utilities, developers, and field verification.
- KPI assurance inputs, audit triggers, and monitoring evidence.
- Additionality, counterfactual, displacement, and net fiscal/economic impact assessment.

## Demo Script

1. Start on **Calibration Analysis**. Show the synthetic 2026-2035 scenario comparison, annual results, deduction/carryforward trace, revenue-neutral parameter ranges, verification requirements, and D7 handoff.
2. Open **Readiness Triage**. Explain how zone records are routed into provisional review pathways before D6 calculations are used.
3. Open **Case Calibration**. Show one gate-cleared case and one blocked case. Emphasize that blocked cases get no instrument, rate, cap, or sunset classification until D4/D5/compliance evidence clears.
4. Open **Evidence & Exports**. Show source-data confidence, model readiness, reconciliation, verification rules, and the downloadable Excel/CSV review package.
5. Open **About / Limitations**. Close with the guardrails: synthetic demo view, D4 legal review, D5/FBR validation, human review, no final legal/fiscal/tax/incentive decision, and no pilot selected by the model.

## Outputs

The pipeline writes local outputs to `outputs/`:

- `zone_triage_prototype.csv`
- `recommendation_explanations.csv`
- `audit_flags.csv`
- `data_quality_issue_log.csv`
- `contradiction_log.csv`
- `data_confidence_scores.csv`
- `activity_classification.csv`
- `field_completeness.csv`
- `calibration_enterprise_inputs.csv`
- `calibration_scenario_definitions.csv`
- `calibration_model_readiness.csv`
- `calibration_excluded_records.csv`
- `calibration_annual_enterprise.csv`
- `calibration_zone_aggregation.csv`
- `calibration_portfolio_summary.csv`
- `calibration_sensitivity.csv`
- `calibration_parameter_ranges.csv`
- `calibration_assumptions.csv`
- `calibration_verification_rules.csv`
- `calibration_reconciliation.csv`
- `calibration_d7_handoff.csv`
- `summary.json`
- `sez_calibration_demo_outputs.xlsx`

The Excel workbook includes D6 review sheets for assumptions, scenario definitions, annual enterprise outputs, zone aggregation, portfolio summary, sensitivity, parameter ranges, verification rules, readiness triage, pathway rationale, validation flags, reconciliation, D7 handoff, summary metadata, reason codes, and limitations.

## D6 Method

See `docs/D6_MODEL_METHOD.md` for model formulas, input conventions, scenario definitions, revenue-neutral parameter search, unresolved policy choices, and D7 handoff logic.

## Limitations

The default public demo uses hypothetical synthetic zones. Outputs are provisional screening outputs for human review. They do not approve incentives, set tax rates, determine fiscal cost, or replace BOI, FBR, Finance Division, SEZA, Law Division, IMF, programme, fiscal modeller, legal counsel, or human review.

Real policy use requires validated BOI/SEZA source records, D4 legal review, D5/FBR fiscal verification, enterprise-level data, KPI validation, and additionality/counterfactual analysis. Reported production or construction is not proof of incentive effectiveness. Additionality and net fiscal/economic impact require separate validation.

This prototype supports the explainable decision layer around fiscal cost analysis, calibration, legal review, and pilot screening. It is not a full policy system, final tax model, or calibration-rate optimizer.
