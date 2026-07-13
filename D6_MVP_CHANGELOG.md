# D6 MVP Changelog

## Final Focused Implementation Pass

- Aligned the demo control layer to the 10 July 2026 Data and Decision Architecture Report.
- Added a governed register covering all 31 report-defined input domains: 2 demonstrated, 20 partial, 4 workflow-only, and 5 not demonstrated.
- Added a sequential readiness funnel, canonical case context, six hard gates, and critical evidence observations.
- Added separate fiscal lenses and an explicit investor-viability gap rather than implying missing project cash flows were calculated.
- Added a hash-bound run manifest with synthetic-only publication state and `NOT_SUBMITTED` approval state.
- Framed Sol Ultra as an evidence-extraction and reconciliation assistant; deterministic code and named specialists retain calculation, validation, and decision authority.

- Retitled the public app to **SEZ D6 Calibration Workbench**.
- Corrected scenario semantics:
  - no-SEZ reference receives no incentive-caused additionality;
  - status quo and accelerated removal are distinct;
  - data-complete non-compliant enterprises can enter accelerated-removal calculations;
  - cost-based regime uses ordinary CIT with no hidden reduced-CIT phase-in;
  - combined transition/pilot blends non-pilot and pilot paths by uptake share.
- Separated model readiness from support eligibility:
  - `evidence_model_ready`
  - `support_eligibility_status`
  - `transition_treatment_status`
  - `blocked_reason`
- Added explicit threshold semantics through `qualifying_expenditure_threshold_pkr_m`.
- Replaced visible ceiling-search output language with a tested joint-configuration frontier against an illustrative D5 fiscal envelope.
- Corrected incentive-caused incremental income so it is zero whenever the selected package, rate, threshold, cap, or utilization setting generates no available incentive.
- Scaled frontier fiscal cost, incremental income, administrative cost, workload, and annual FTE consistently by pilot uptake.
- Replaced the visible marginal range card with the current joint configuration and nearest feasible tested configuration.
- Corrected annual FTE so it is based on peak annual review workload rather than total projection-period hours.
- Added fiscal identities for benchmark tax liability, tax collected, tax expenditure, cash net revenue, and fiscal impact versus reference.
- Added administrative workload and cost assumptions using review hours, audit sample rate, and cost per review hour.
- Added operational D7 recalibration triggers.
- Updated synthetic archetypes so rate, cap, package, threshold, utilization, and uptake controls have visible economic effects.
- Added economic-coherence regression tests. Current suite covers 59 tests.

## Guardrails Preserved

- Public/default app remains synthetic demo view.
- No real BOI, SEZA, FBR, Finance, legal, developer, or enterprise data is invented.
- No final legal, fiscal, tax, incentive, or pilot decision is made.
- D4 legal review and D5/FBR fiscal validation remain required before policy use.
- Scenario Settings remains hidden unless `SHOW_ADVANCED_SCENARIOS=1`.
