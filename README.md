# SEZ Zone Triage and Calibration Support MVP

v0.5-lite - demoable SEZ Zone Triage and Calibration Support MVP

This repo is intentionally scoped to a lightweight demo flow. It is not a full policy system, final tax model, or calibration rate optimizer.

Demo flow:

`zone data -> data quality checks -> data confidence score -> activity classification -> legal/fiscal placeholder gates -> provisional recommendation -> reason codes -> export`

Hard guardrails:

- Demo only.
- No final legal, fiscal, or incentive decisions.
- No final tax rates.
- Any support-related output is subject to D4 legal review and D5 fiscal verification.
- Any cost-based support is temporary transition support only; all SEZ fiscal incentives phase out by 30 June 2035.
- Current normalized data is the 35-zone demo dataset, not the final reconciled 44/54-zone universe.

## Dataset Scope

The current normalized dataset covers **35 detected zone profile records** and **35 normalized indicator records** based on the source digest. The source digest says the normalized CSV was created from detected zone profile rows and 2026 colonization metrics where reliable normalization was possible.

Exact row-level verification should use the original workbook. This MVP preserves uncertainty, missing fields, source-scope mismatch, contradiction logs, and data-quality flags instead of pretending the normalized dataset is complete.

## What It Does

- Loads `data/SEZ_Key_Indicators_Normalized.csv`.
- Normalizes inconsistent column names and preserves unknown fields.
- Uses `data/legal_fiscal_placeholders.csv` for demo-only legal/fiscal placeholder gates.
- Logs missing fields, impossible values, contradictions, and source-scope issues.
- Scores data confidence from source reliability, completeness, consistency, cross-source placeholder scoring, and recency.
- Classifies zones as productive, moving toward production, inactive, speculative/vacant, or unclear.
- Applies placeholder gates before provisional recommendations.
- Exports CSVs and a demo Excel workbook.
- Provides a Streamlit demo interface.

## What It Does Not Do

- It does not calculate final tax liability.
- It does not replace fiscal modelling, D4 legal review, D5/FBR/customs verification, or human review.
- It does not make final policy decisions or grant incentives.
- It does not calculate final deduction rates or final incentive decisions.
- It does not include market distortion analysis, institutional role mapping, concept-note alignment, legislative sequencing, milestone mapping, or rate optimization.

## Install

```bash
pip install -r requirements.txt
```

## Run CLI

```bash
python run_demo.py
```

Expected output includes loaded zone count, data-quality issues, confidence scores, provisional recommendations, possible screen candidates, and the output folder path.

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

Legal fields are placeholders pending D4 legal review. Fiscal exposure fields are placeholders pending D5/FBR/customs verification. Enterprise and plot-level data are not fully loaded. The current normalized data is the 35-zone demo dataset, not the final reconciled 44/54-zone universe. Recommendations are provisional and for demonstration only. Human review is mandatory.

## Next Development Steps

Future phases can add D4 legal classifications, D5 fiscal exposure outputs, canonical zone registry work, enterprise/plot-level outcome data, validated fiscal caps, and audit workflow. They are intentionally outside v0.5-lite.
