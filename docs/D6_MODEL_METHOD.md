# D6 Model Method

This document describes the synthetic D6 calibration proof of concept. It is an executable architecture and governed workflow demonstration, not a validated fiscal model or final policy recommendation.

## Scenario Definitions

| Scenario | Meaning |
| --- | --- |
| `no_sez_specific_incentive` | Ordinary-reference CIT path. No SEZ-specific deduction and no incentive-caused incremental activity. |
| `status_quo_to_2035` | Existing protected treatment through natural expiry or the 30 June 2035 hard cap where assumed. |
| `accelerated_removal` | Data-complete non-compliant enterprises move earlier to ordinary CIT. Compliant records remain on status quo. |
| `cost_based_regime` | Ordinary CIT plus temporary cost-based deductions for synthetic support-review-ready records only. No hidden CIT phase-in. |
| `combined_transition_pilot` | Blends the applicable non-pilot treatment and full cost-based pilot treatment by explicit uptake share. |

## Model Readiness Versus Policy Eligibility

`evidence_model_ready` means the synthetic enterprise has enough financial evidence to calculate the scenario.

It does not mean the enterprise should receive support. The model separately reports:

- `support_eligibility_status`
- `transition_treatment_status`
- `blocked_reason`

A data-complete non-compliant enterprise can therefore be model-ready for accelerated-removal calculations while being blocked from new cost-based support review.

## Counterfactual And Additionality

The no-incentive reference path receives no incentive-caused incremental income.

For incentive scenarios, incremental assessed income is a synthetic structural assumption, not a causal estimate:

```text
incremental_assessed_income_t =
  prior_year_responsive_expenditure_after_incentive_intensity
  * scenario_additionality_share
  * taxable_return_on_incremental_expenditure
```

The `low`, `base`, and `high` additionality cases are sensitivity assumptions. Reported production or construction is not treated as proof that incentives caused activity.

For the cost-based scenario, responsive expenditure is conditional on an actual positive incentive being generated and available. The model first computes a transparent incentive-intensity factor from the selected instrument package, rate, annual qualifying threshold, annual cap, and utilization setting. If no deduction is generated or available, the incentive-intensity factor is zero and incentive-caused incremental assessed income is zero.

## Fiscal Identities

The model distinguishes the core fiscal measures:

```text
benchmark_tax_liability = assessed_income_before_relief * statutory_cit_rate
tax_collected = tax_due
tax_expenditure = benchmark_tax_liability - tax_collected
cash_net_revenue = tax_collected - incremental_admin_cost - other_government_cash_cost
fiscal_impact_vs_reference = cash_net_revenue - ordinary_reference_tax
gross_fiscal_cost = tax_expenditure + customs_expenditure + incremental_admin_cost + other_government_cash_cost
```

The model does not subtract tax expenditure from tax collected and call that net fiscal position. `cash_net_revenue` is the cash concept; `tax_expenditure` is the benchmark-relative foregone-revenue concept.

## Cost-Based Deduction Formula

The cost-based scenario applies ordinary CIT first, then temporary deductions:

```text
ordinary_capex_offset = capex / ordinary_capex_depreciation_years
capex_incremental_deduction = max(0, capex * capex_deduction_rate - ordinary_capex_offset)
rd_incremental_deduction = rd_spend * (rd_super_deduction_total_rate - 1)
training_incremental_deduction = training_spend * (training_super_deduction_total_rate - 1)
```

The default cost-based scenario does not include a reduced-CIT phase-in.

## Threshold Semantics

`qualifying_expenditure_threshold_pkr_m` is a minimum annual qualifying expenditure threshold. If total annual qualifying CAPEX/R&D/training expenditure is below the threshold, no new deduction claim is generated for that enterprise-year.

If the threshold is met:

```text
deduction_generated =
  min(incremental_deduction_base * utilization_rate, annual_deduction_cap_pkr_m)
```

Unused deductions carry forward FIFO for the configured number of years. Tax due is never allowed to fall below zero.

## Fiscal Envelope And Tested Joint Configurations

`d5_fiscal_envelope_pkr_m` is an illustrative synthetic ceiling. It is not a validated D5 fiscal estimate.

The tested joint-configuration frontier uses a transparent grid over:

- instrument package
- CAPEX rate
- annual cap
- qualifying threshold
- utilization rate
- pilot uptake
- additionality case

For each combination the model reports:

- tested fiscal cost
- fiscal envelope
- feasible/infeasible flag
- binding constraint
- incremental assessed income
- administrative workload and cost
- verification burden

Pilot uptake is part of the tested joint configuration. Tested fiscal cost, incremental assessed income, administrative cost, review workload, and FTE are all scaled by the selected uptake share. If the whole tested grid is feasible, the output says no binding upper bound was identified within the tested grid. If no combination is feasible, it says no feasible setting was found.

## Uptake Blending

For `combined_transition_pilot`:

```text
combined_result =
  non_pilot_result * (1 - pilot_uptake_share)
  + full_cost_based_pilot_result * pilot_uptake_share
```

A 0% uptake setting equals the applicable non-pilot treatment. A 100% uptake setting equals the full pilot treatment for the pilot cohort. Intermediate uptake interpolates consistently.

## Administrative-Cost Method

Administrative feasibility is illustrative and uses:

```text
review_hours =
  admin_review_hours_per_claim
  + admin_audit_hours_per_claim * audit_sample_rate

admin_cost =
  fixed_admin_cost_per_claim_pkr_m
  + review_hours * admin_cost_per_review_hour_pkr_m
```

The model reports total review workload hours, peak annual review workload hours, and indicative annual FTE requirements. FTE is based on peak annual workload divided by annual FTE hours, not total projection-period hours. These are capacity assumptions, not validated institutional estimates.

## D7 Recalibration Rules

The D7 handoff table includes proposed pilot triggers:

- fiscal cost exceeds the approved envelope
- verified additionality falls below the agreed assumption
- claim-disallowance rate exceeds threshold
- processing time or audit backlog exceeds capacity
- uptake is materially outside the expected range
- compliance or verification failure occurs

For each trigger the output identifies metric, threshold, review frequency, data owner, decision owner, default action, and affected parameter.

## Remaining Unresolved Choices

- Valid D5 fiscal envelope and national scaling.
- D4 legal authority, grandfathering, and transition commitments.
- FBR/customs validation of tax and exemption records.
- Final treatment of customs exemptions.
- Additionality and counterfactual evidence.
- Displacement and market-distortion analysis.
- Pilot zone and enterprise selection.
- Final claim-verification rules and disallowance process.
