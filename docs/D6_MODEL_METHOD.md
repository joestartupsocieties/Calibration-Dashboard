# D6 Calibration Model Method

This document describes the thin-slice quantitative model used in the synthetic demo build. It is for workflow review only. It does not approve incentives, set tax rates, determine final fiscal cost, or replace BOI, FBR, Finance Division, SEZA, legal, IMF, programme, fiscal-modelling, or human review.

## Scope

The model connects enterprise-level synthetic evidence to D6 calibration analysis:

- 2026-2035 annual enterprise projection.
- Status-quo revenue-foregone baseline.
- Accelerated-removal scenario.
- Cost-based regime scenario.
- Combined transition plus pilot scenario.
- No-SEZ-specific-incentive reference state.
- Zone and portfolio aggregation using explicit sample weights.
- Revenue-neutral parameter search against a D5 fiscal envelope placeholder.
- D7 pilot handoff fields for verification, monitoring, and launch dependencies.

The public/default app uses a synthetic demo dataset. Real use requires validated BOI/SEZA/FBR/Finance/legal source data, enterprise-level evidence, and D4/D5 clearance.

## Core Input Conventions

Enterprise-level data is preferred for D6 calculations. Zone-level totals are treated as control totals for reconciliation rather than added again.

- USD inputs are converted to PKR using `fx_pkr_per_usd`.
- `cit_foregone_pkr_m_2026` and `tax_paid_pkr_m_2026` are used to infer a benchmark tax base.
- `customs_exemption_pkr_m_cumulative` is cumulative and is annualized only through the explicit customs schedule.
- CAPEX/R&D/training values are claim-base inputs for illustrative deduction modelling.
- Enterprise records are excluded from D6 calculations unless legal, fiscal, compliance, cohort-scope, and benchmark-tax checks clear.
- EPZ records are excluded from the default SEZ calibration slice.

## Formula Summary

Benchmark tax:

```text
ordinary_benchmark_tax = cit_foregone_2026 + tax_paid_2026
baseline_assessed_income = ordinary_benchmark_tax / statutory_cit_rate
benchmark_tax_year_t = assessed_income_year_t * statutory_cit_rate
```

Growth:

```text
assessed_income_year_t = baseline_assessed_income * (1 + assessed_income_growth)^t
eligible_expenditure_year_t = 2026_eligible_expenditure * (1 + eligible_expenditure_growth)^t
```

Additionality:

```text
incremental_assessed_income_year_t =
  prior_year_qualifying_expenditure * additionality_share * taxable_return_on_incremental_expenditure
```

The model reports low/base/high additionality cases. Reported production or construction is not treated as proof that incentives caused activity.

Status quo:

```text
tax_due = benchmark_tax * (1 - current_holiday_exemption_share) through 2035
direct_CIT_expenditure = benchmark_tax - tax_due
customs_expenditure = cumulative_customs_exemption / customs_annualization_years during the schedule only
```

Cost-based regime:

```text
ordinary_capex_offset = capex / ordinary_capex_depreciation_years
capex_incremental_deduction = max(0, capex * capex_deduction_rate - ordinary_capex_offset)
rd_incremental_deduction = rd_spend * (rd_super_deduction_total_rate - 1)
training_incremental_deduction = training_spend * (training_super_deduction_total_rate - 1)
deduction_generated = min((capex + rd + training increments) * utilization_rate, annual_deduction_cap)
taxable_income_after_deduction = max(0, assessed_income - deduction_used)
tax_due = taxable_income_after_deduction * statutory_cit_rate * phase_in_factor
```

Unused deductions may carry forward for the configured number of years and are used FIFO. Tax is floored at zero.

Portfolio aggregation:

```text
weighted_value = enterprise_value * aggregation_weight
NPV = sum(weighted_value_year_t * discount_factor_year_t)
```

Revenue-neutral search:

The parameter search tests whether a cost-based setting remains within the fiscal envelope. If no D5 envelope is supplied, the synthetic proxy envelope is the NPV gross fiscal cost of the status-quo-to-2035 scenario.

## Scenarios

| Scenario | Use |
| --- | --- |
| Status quo to 2035 | Baseline fiscal-cost envelope scenario. |
| Accelerated removal | Transition scenario for non-compliant zones or enterprises. |
| Cost-based regime | Candidate CAPEX/R&D/training deduction scenario tested against the envelope. |
| Combined transition plus pilot | Cost-based pilot uptake combined with transition logic. |
| No SEZ-specific incentive | Reference tax benchmark, not a transition-policy substitute. |

## Output Review Checks

Reviewers should inspect:

- `calibration_model_readiness.csv` before using any numeric output.
- `calibration_reconciliation.csv` to identify enterprise-vs-zone control mismatches.
- `calibration_parameter_ranges.csv` before discussing caps or rates.
- `calibration_verification_rules.csv` before discussing administrative feasibility.
- `calibration_d7_handoff.csv` before translating D6 outputs into D7 pilot design.

## Unresolved Policy Inputs

The thin-slice model intentionally keeps these choices explicit:

- D5 fiscal envelope amount.
- Legal status and grandfathering/sunset constraints from D4.
- Cohort eligibility policy for the cost-based regime.
- Enterprise claim-verification rules and disallowance rules.
- Treatment of carry-forward after 30 June 2035.
- FBR/customs validation of tax and exemption records.
- Additionality, counterfactual, displacement, and net-impact evidence.
- Whether any pilot should launch, and if so which zones or enterprises are selected.

No pilot zone is selected by this model.
