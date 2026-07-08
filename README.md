# SEZ Incentive Transition Triage

Provisional decision-support for legal, fiscal, data-confidence, and pilot-readiness review.

This repository is scoped to a demoable screening flow using fully synthetic hypothetical-zone records by default. It does not make final legal, fiscal, tax, or incentive decisions, does not set final tax rates, determine fiscal cost, or replace BOI, FBR, Finance Division, SEZA, Law Division, IMF, programme, fiscal modeller, legal counsel, or human review.

## Demo Flow

`zone data -> validation flags -> data confidence score -> activity classification -> legal/fiscal validation gates -> provisional treatment -> reason codes -> export`

Hard guardrails:

- Prototype only.
- Outputs are provisional and subject to validation.
- Human review is required.
- Any support-related output remains subject to D4 legal review and D5/FBR fiscal verification.
- Any cost-based support is temporary transition support only; all SEZ fiscal incentives phase out by 30 June 2035.
- The default public/MVP demo uses fully synthetic hypothetical zones and must remain synthetic unless an authorized internal user explicitly switches profiles.

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

The app opens to **Executive Triage** in **Synthetic demo view** for a 3-5 minute walkthrough.

To run the default public/MVP synthetic demo:

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

The default MVP demo uses `data/synthetic/SEZ_Key_Indicators_Normalized.csv` and `data/synthetic/legal_fiscal_placeholders.csv`. These files contain hypothetical synthetic zones only, including synthetic D4 legal status, D5/FBR fiscal exposure bands, additionality/counterfactual/effectiveness flags, KPI and pilot-readiness fields, and enterprise-level summaries.

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

1. Start on **Executive Triage**. Explain that the prototype organizes demo-zone records into provisional review pathways; it does not approve incentives or calculate tax/fiscal impacts.
2. Open **Case Review**. Show one selected case as a human-review screening note with review pathway, reason codes, open gates, next action, validation owner, and human review required.
3. Open **Data Confidence**. Explain how the app preserves uncertainty, validation flags, source-scope limits, and synthetic-data caveats instead of treating the dataset as complete.
4. Open **Export**. Generate structured CSV/Excel outputs and a selected-zone screening note for review or follow-up work.
5. Open **About / Limitations**. Close with the guardrails: synthetic demo view, D4 legal review, D5/FBR validation, human review, and no final legal, fiscal, tax, or incentive decision.

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
- `summary.json`
- `sez_calibration_demo_outputs.xlsx`

## Limitations

The default public/MVP demo uses hypothetical synthetic zones. Outputs are provisional screening outputs for human review. They do not approve incentives, set tax rates, determine fiscal cost, or replace BOI, FBR, Finance Division, SEZA, Law Division, IMF, programme, fiscal modeller, legal counsel, or human review.

Real policy use requires validated BOI/SEZA source records, D4 legal review, D5/FBR fiscal verification, enterprise-level data, KPI validation, and additionality/counterfactual analysis. Reported production or construction is not proof of incentive effectiveness. Additionality and net fiscal/economic impact require separate validation.

This prototype supports the explainable decision layer around fiscal cost analysis, calibration, legal review, and pilot screening. It is not a full policy system, final tax model, or calibration-rate optimizer.
