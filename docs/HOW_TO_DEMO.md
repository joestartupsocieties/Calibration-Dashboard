# How To Demo

## Three-Minute Script

1. Start the app with `streamlit run app.py`.
2. Open Home and show the provisional-use warning.
3. Point out that 35 zones are loaded from the normalized source-digest dataset.
4. Open Data Quality and show missing fields, contradictions, field completeness, and confidence distribution.
5. Open Zone Explorer and select one zone to show raw normalized fields and source lineage.
6. Open Recommendation Engine and show the provisional treatment.
7. Decode the reason codes and hard gates for the selected zone.
8. Explain that legal and fiscal fields are placeholders pending D4 legal review and D5/FBR/customs verification.
9. Open Export and download the CSV or Excel outputs.

## Presenter Notes

The key message is not that the model makes final decisions. The demo shows a reproducible logic chain that keeps uncertainty visible and routes zones to the right next review step.
