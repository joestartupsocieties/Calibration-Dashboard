# MVP Spec

Version: v0.4 - Zone Triage and Explainable Recommendation Engine

The MVP is a reproducible demo pipeline built from `/data` and `/config`. It does not hard-code workbook output tabs. The step-2 workbook and source digest are design and lineage references.

## Pipeline

1. Load and normalize `SEZ_Key_Indicators_Normalized.csv`.
2. Generate missing legal and fiscal placeholder tables.
3. Run data-quality and contradiction checks.
4. Score data confidence.
5. Classify activity.
6. Apply legal/compliance and data hard gates.
7. Generate recommendation explanations.
8. Export CSV and Excel outputs.

## Decision Standard

The engine uses hard gates before treatment language. Because legal and fiscal data are placeholders, outputs use provisional language such as possible pilot screen candidate, transition candidate, non-fiscal support only, more data required, legal review required, or sanction/cure review.
