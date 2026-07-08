# Explainable SEZ Incentive Calibration Framework - Demo MVP

v0.4 - Zone Triage and Explainable Recommendation Engine

This is a demoable MVP for explainable SEZ incentive calibration. It loads normalized zone-level data, runs data-quality checks, calculates transparent confidence scores, classifies activity status, applies legal/compliance hard gates, and produces provisional treatment recommendations with reason codes and explanation trails.

## Dataset Scope

The current normalized dataset covers **35 detected zone profile records** and **35 normalized indicator records** based on the source digest. The source digest says the normalized CSV was created from detected zone profile rows and 2026 colonization metrics where reliable normalization was possible.

Exact row-level verification should use the original workbook. This MVP preserves uncertainty, missing fields, source-scope mismatch, contradiction logs, and data-quality flags instead of pretending the normalized dataset is complete.

## What It Does

- Loads `data/SEZ_Key_Indicators_Normalized.csv`.
- Normalizes inconsistent column names and preserves unknown fields.
- Creates legal and fiscal placeholder tables if they are missing.
- Logs missing fields, impossible values, contradictions, and source-scope issues.
- Scores data confidence from source reliability, completeness, consistency, cross-source placeholder scoring, and recency.
- Classifies zones as productive, moving toward production, inactive, speculative/vacant, or unclear.
- Applies hard gates before recommendations.
- Exports CSVs and a demo Excel workbook.
- Provides a Streamlit demo interface.

## What It Does Not Do

- It does not calculate final tax liability.
- It does not replace fiscal modelling, D4 legal review, D5/FBR/customs verification, or human review.
- It does not make final policy decisions or approve incentives.
- It does not calculate final deduction rates or final incentive eligibility.

## Install

```bash
pip install -r requirements.txt
```

## Run CLI

```bash
python run_demo.py
```

Expected output includes loaded zone count, data-quality issues, confidence scores, provisional recommendations, pilot screen candidates, and the output folder path.

## Run Streamlit

```bash
streamlit run app.py
```

## Outputs

The demo writes:

- `outputs/zone_triage_prototype.csv`
- `outputs/recommendation_explanations.csv`
- `outputs/audit_flags.csv`
- `outputs/data_quality_issue_log.csv`
- `outputs/contradiction_log.csv`
- `outputs/data_confidence_scores.csv`
- `outputs/activity_classification.csv`
- `outputs/field_completeness.csv`
- `outputs/summary.json`
- `outputs/sez_calibration_demo_outputs.xlsx`

## Known Limitations

Legal fields are placeholders pending D4 legal review. Fiscal exposure fields are placeholders pending D5/FBR/customs verification. Enterprise and plot-level data are not fully loaded. The 35-zone normalized dataset does not equal the full 44/54-zone universe. Recommendations are provisional and for demonstration only. Human review is mandatory.

## Next Development Steps

- Replace legal placeholders with D4 legal classification outputs.
- Replace fiscal placeholders with D5/FBR/customs fiscal exposure outputs.
- Add canonical zone registry and alias table.
- Add enterprise/plot-level outcome data.
- Add validated fiscal caps and audit workflow.
