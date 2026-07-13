# Data and Decision Architecture Fit-Gap Assessment

## Source and conclusion

This assessment uses `SEZ Incentive Calibration Dashboard - Data and Decision Architecture Report.docx` dated 10 July 2026 as the controlling requirements report. The report defines the dashboard as a governed control plane around a versioned calculation service and a human decision process.

The existing platform is strongest as an executable synthetic D6 calculation demonstrator. It already supports distinct transition scenarios, joint CAPEX/R&D/training settings, annual and NPV fiscal outputs, an illustrative D5 envelope, low/base/high additionality assumptions, weighted enterprise archetypes, administrative burden, and D7 recalibration triggers.

It is not yet the decision-grade evidence platform described by the report. The largest gaps are canonical source observations, effective dating, clause-level legal facts, detailed FBR/customs/accounts records, investor project cash flow, independent model validation, maker-checker approval, and production security controls.

The report defines 31 input domains. Current demo coverage is:

- 2 domains demonstrated end to end with synthetic inputs.
- 20 domains partially demonstrated.
- 4 domains represented as workflow or gates without substantive evidence.
- 5 domains not demonstrated in the current thin slice.

These are architecture/demo-coverage counts. No synthetic observation is validated for policy use.

## Capability fit

| Report capability | Current fit | What already exists | Material gap |
| --- | --- | --- | --- |
| Reconciled case register | Partial | Stable synthetic zone and enterprise IDs; reconciliation output; case view | No canonical zone-developer-enterprise-project-instrument hierarchy; alias crosswalk; match confidence; or effective dating |
| Legal and fiscal gates | Partial | Legal risk; compliance; fiscal-data; source-confidence; and model-readiness gates | No provision; clause; obligation; default; cure; or exception ledger validated by D4/D5 owners |
| Instrument calibration | Moderate demo fit | CAPEX; R&D; training; package; rate; threshold; cap; utilization; carry-forward; and 2035 sunset | No project viability gap; line-level qualifying expenditure; or complete ordering and anti-stacking rules |
| Scenario comparison | Moderate demo fit | S1-S4-style paths; ordinary reference; annual/NPV output; additionality sensitivity | Official static revenue foregone is not separately reconciled; no investor NPV/IRR/payback/EATR/EMTR |
| KPI and additionality | Partial | Activity; KPI summaries; confidence; low/base/high assumptions; D7 triggers | No matched comparator; relocation evidence; project counterfactual; or causal validation |
| Pilot and rollout | Partial | Pilot uptake; audit burden; FTE; and recalibration triggers | No live quarterly claims; errors; appeals; monitoring; or authorized pilot-cohort decision |
| Audit and approvals | Partial | Model version; assumptions provenance; reason codes; exports; hash-bound run manifest | No frozen production snapshot service; challenger approval; maker-checker queue; override ledger; or publication lifecycle |

## Data-model gaps

The current platform partly represents zone, enterprise, cohort, fiscal-summary, qualifying-expenditure, legal/fiscal readiness, weighting, scenario, verification, and D7 handoff data.

The following structures remain missing or insufficient:

- observation versus validated-value records with source locator, file hash, provider, validator, valid time, and system time;
- canonical alias crosswalks and the full zone to developer to enterprise/cohort to project to package to period case grain;
- statutory provisions, contractual clauses, obligations, defaults, cures, remedies, and no-double-benefit rule versions;
- tax returns and assessments, minimum-tax interactions, opening loss vintages, and actual generated-versus-used benefits;
- full financial statements and project cash flows for investor viability testing;
- asset, invoice, payment, and customs declaration lines with placed-in-service dates;
- public infrastructure, land, utility, and administration cost schedules with allocation controls;
- comparator cohorts, counterfactual surveys, relocation/displacement evidence, and validated additionality methods;
- long-form run-by-scenario-by-case-by-instrument-by-metric-by-year results; and
- maker-checker decisions, overrides, approvals, and publication states tied to frozen evidence.

## Quantitative-method fit

### Credible for the synthetic demonstration

- Distinct ordinary-reference and transition paths.
- Explicit CAPEX/R&D/training mechanics.
- Threshold, cap, utilization, carry-forward, and sunset treatment.
- Zero incentive-caused benefit when no positive incentive is available.
- Annual and NPV fiscal identities.
- Joint configuration frontier and nearest feasible tested configuration.
- Pilot-uptake scaling and annual administrative FTE.
- Low/base/high additionality sensitivity and D7 triggers.

### Not decision-grade

- The assessed-income proxy is not an FBR return or assessment record.
- Opening tax losses, minimum/other tax, and actual benefit utilization are absent.
- Static revenue foregone requires a separate FBR benchmark reconciliation.
- Investor project cash flow, hurdle rate, NPV, IRR, payback, EATR, and EMTR are absent.
- The frontier tests synthetic fiscal cost; it does not identify the minimum support needed to close a validated viability gap.
- Customs and public/indirect costs lack source-level reconciliation.
- Additionality remains an assumption range rather than a causal estimate.

## Demo-critical implementation

The optimized five-page demo now keeps the existing calculation engine and adds the minimum report-aligned control layer:

1. **Calibration Analysis** shows the selected joint decision, nearest feasible tested configuration, separated fiscal lenses, investor-viability gap, uncertainty, verification, and D7 triggers.
2. **Input Readiness** shows all 31 report-defined input domains, their workflow state, owner, validator, field mapping, decision consequence, next action, and a sequential readiness funnel.
3. **Case Calibration** shows canonical case context, six hard gates, critical asserted observations, selected run, approval state, reason codes, and blocked investor viability.
4. **Evidence & Exports** shows the run manifest, model readiness, reconciliation, verification rules, validation flags, and controlled exports.
5. **About / Limitations** preserves the synthetic-data boundary and specialist authority.

## Sol Ultra role

Sol Ultra should accelerate evidence preparation rather than become the decision engine. Appropriate uses are:

- extract candidate observations and exact clause or record locators from approved documents;
- propose entity aliases and crosswalks with match confidence;
- identify unit, period, definition, and source conflicts;
- draft validation notes and owner-specific data requests;
- generate source-linked transformation code and boundary tests; and
- check whether a result can be reproduced from the run manifest.

Every Sol Ultra output should enter as an asserted, unvalidated observation. Sol Ultra must not validate its own extraction, infer legal authority, set fiscal parameters, decide treatment, authorize a package, or override a named specialist.

## Out of scope for this demo

- Production database, object storage, API, and FBR secure-enclave integration.
- Raw taxpayer or confidential legal data.
- Full production relational model and all ten report screens.
- Every candidate instrument in the report.
- Black-box optimization or a final rate.
- Final legal, fiscal, tax, pilot, or incentive authorization.

## Recommended 3-5 minute walkthrough

1. Show the 31-domain register and sequential readiness funnel.
2. Open one case and trace its canonical identity, six gates, and critical observations.
3. Show how unresolved D4, D5, or counterfactual evidence blocks a decision metric.
4. Run the S1-S4-style comparison and change one joint parameter.
5. Show the envelope decision, nearest feasible tested configuration, and additionality sensitivity.
6. Show that investor viability is not calculated without project cash-flow evidence.
7. Open the run manifest and export the governed workbook.
8. Close with approval state: not submitted; independent legal, fiscal, model, and policy review required.

## Bottom line

The platform already demonstrates useful D6 logic. The report's central product, however, is the governed chain from source observation to validated fact to frozen run to authorized decision. The optimized demo makes that chain visible without pretending the missing legal, tax, investor-viability, security, or approval layers already exist.
