# SEZ Fiscal-Calibrated Triage & Incentive Screening Prototype

Decision-support prototype for SEZ fiscal exposure, legal/compliance triage, calibration logic, and pilot screening.

This repository is scoped to a demoable screening flow. It does not make final legal, fiscal, tax, or incentive decisions, does not set final tax rates, and does not replace BOI, FBR, Finance, SEZA, legal, IMF, programme, or human review.

## Demo Flow

`zone data -> validation flags -> data confidence score -> activity classification -> legal/fiscal validation gates -> provisional treatment -> reason codes -> export`

Hard guardrails:

- Prototype only.
- Outputs are provisional and subject to validation.
- Human review is required.
- Any support-related output remains subject to D4 legal review and D5/FBR fiscal verification.
- Any cost-based support is temporary transition support only; all SEZ fiscal incentives phase out by 30 June 2035.
- The current source package is the 35-zone demo dataset, not the final reconciled 44/54-zone universe.

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

The app opens with Demo Mode on by default for a 3-5 minute walkthrough.

## Demo And Source Data

The current structured screening dataset covers 35 detected zone profile records and 35 normalized indicator records based on the source digest. The source digest says the CSV was created from detected zone profile rows and 2026 colonization metrics where reliable normalization was possible.

Exact row-level verification should use the original workbook and source documents before policy use. The prototype preserves uncertainty, missing fields, source-scope mismatch, cross-source/status conflicts, and validation flags instead of treating the dataset as complete.

If `data/SEZ_Key_Indicators_Normalized.csv` is missing, the pipeline creates a clearly marked synthetic demo dataset so the app can still run.

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

1. Start on Executive View and explain that the tool is a provisional decision-support layer, not a final decision system.
2. Show Zone Explorer for the reported-production demo case and point out the clean zone summary and additionality caveat.
3. Open Recommendation Engine and show provisional treatment, open validation gates, reason codes, calibration output, next action, validator, and human review.
4. Switch to the low-data-confidence demo case and show why the output is more data required.
5. Switch to the legal/fiscal review case and show D4 legal and D5/FBR validation requirements.
6. Open Scenario Settings and compare Base, IMF strict triage, Data-quality conservative, and Pilot-readiness screen.
7. Open Export, generate the selected-zone memo, and show the CSV/memo outputs.

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

Legal, fiscal, compliance, enterprise-level, and additionality fields are not yet validated for policy use. Fiscal exposure and FBR/customs inputs remain pending D5 verification. Legal status remains pending D4 review. Reported production or construction is not proof of incentive effectiveness. Additionality and net fiscal/economic impact require separate validation.

This prototype supports the explainable decision layer around fiscal cost analysis, calibration, legal review, and pilot screening. It is not a full policy system, final tax model, or calibration-rate optimizer.
