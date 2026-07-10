# Economic Coherence Checks

The final pass adds regression tests and numeric validation for the D6 calibration proof of concept.

## Scenario Behavior

- Status quo and accelerated removal differ for a data-complete non-compliant archetype.
- Accelerated removal collects at least as much tax and costs no more than continued protected treatment for that archetype.
- Combined pilot output at 0%, intermediate, and 100% uptake interpolates consistently.
- The combined pilot is not automatically identical to the full cost-based regime.
- The no-SEZ reference receives no incentive-caused additionality.

## Parameter Behavior

- CAPEX rate changes affect results when the cap and tax capacity do not bind first.
- Annual cap changes affect results when the cap binds.
- Instrument-package changes affect relevant archetypes.
- Qualifying threshold changes the claim base by blocking claims below the threshold.
- Utilization changes deduction use.
- Discount rate changes NPV while annual undiscounted cash flows remain formula-driven.
- Binding constraints are reported as threshold, annual cap, utilization, tax capacity/carryforward, fiscal envelope, or non-binding within the tested range.

## Fiscal Arithmetic

- Tax expenditure equals benchmark tax liability minus tax collected.
- Cash net revenue equals tax collected minus actual cash administrative and other government cash costs.
- Fiscal impact versus reference reconciles to cash net revenue minus ordinary reference tax.
- Tax due is floored at zero.
- Carryforward balances remain non-negative and reconcile through FIFO use/expiry.
- Weighted portfolio totals reconcile to enterprise-year values.

## Frontier Behavior

- The synthetic D5 envelope produces both feasible and infeasible parameter combinations.
- The default frontier reports tested fiscal cost, envelope margin, feasible flag, binding constraint, incremental assessed income, and administrative workload.
- Non-binding ranges are labelled as non-binding within the tested range instead of as calibrated maxima.
- No-feasible cases are handled by explicit status labels.
- Every sensitivity row carries the fiscal-envelope value and definition.

## Public-Demo Guardrails

- Model readiness and support-review status are distinct.
- “None” is not counted as an open gate.
- Public outputs are synthetic and provisional.
- No output claims causal econometric estimation or actual Pakistan policy evidence.

