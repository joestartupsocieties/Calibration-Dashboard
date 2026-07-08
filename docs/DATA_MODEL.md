# Data Model

## Primary Zone Data

Primary file: `data/SEZ_Key_Indicators_Normalized.csv`.

The normalizer lowercases columns, strips whitespace, replaces punctuation with underscores, maps likely synonyms, and preserves unknown fields. Missing canonical fields are created as blank columns so downstream modules do not crash.

## Placeholder Tables

`data/legal_compliance_placeholder.csv` is generated when missing. Defaults mark legal risk, grandfathering risk, developer compliance, enterprise compliance, and reform space as unknown, with legal review required.

`data/fiscal_exposure_placeholder.csv` is generated when missing. Fiscal numeric fields are blank, fiscal exposure is unknown, and fiscal data confidence is missing.

## Output Tables

The core output is `outputs/zone_triage_prototype.csv`, backed by confidence, activity classification, data-quality, contradiction, audit-flag, and explanation tables.
