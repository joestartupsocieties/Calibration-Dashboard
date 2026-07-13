# REMIT Demo Runbook

## Demo objective

In 3-5 minutes, show one controlled decision:

> Is the selected joint incentive configuration within the illustrative D5 fiscal envelope, and if not, what is the nearest feasible tested configuration?

Keep the demonstration synthetic and provisional. Do not imply legal clearance, fiscal validation, pilot selection, or incentive authorization.

## Locked cases

- **Model-ready calculation case:** `SYN-001 - Indus Productivity SEZ`
  - Synthetic enterprise financial inputs are sufficient to execute the calculator.
  - It remains subject to all six real-use validation gates and human review.
- **Blocked calculation case:** `SYN-011 - Sulaiman Data Gap SEZ`
  - Enterprise assessed-income evidence is incomplete.
  - The case cannot enter calibration use until the minimum-data gate is resolved.

## Timed walkthrough

### 0:00-1:15 - Calibration Analysis

1. Open **Calibration Analysis**.
2. State: "The workbench tests whether a joint temporary incentive configuration fits an illustrative fiscal envelope. It does not authorize an incentive or determine final fiscal cost."
3. Point to the default decision:
   - selected configuration is outside the illustrative envelope;
   - the envelope margin is negative; and
   - the nearest feasible tested configuration is shown beside it.
4. Point to the fiscal lenses:
   - direct tax-expenditure output;
   - behavioural/counterfactual effect;
   - administration cost;
   - cash fiscal impact versus reference;
   - static revenue foregone is not separately reconciled; and
   - investor viability is not calculated.

Do not change several controls. If interaction is useful, change only one parameter and explain that the run is regenerated from the same deterministic pipeline.

### 1:15-2:15 - Model-ready case

1. Open **Case Calibration**.
2. Select **Indus Productivity SEZ - Punjab**.
3. Show canonical case context, selected run, and the six hard gates.
4. State: "Model-ready means the synthetic calculator can run. It does not mean support-ready, legally cleared, fiscally validated, or authorized."
5. Point to **Investor viability: Not calculated** and **Not submitted - human review required**.

### 2:15-3:00 - Blocked case

1. Select **Sulaiman Data Gap SEZ - Not available**.
2. Show the blocked D6 model status and minimum-data gate.
3. State: "This is the safeguard: incomplete assessed-income evidence keeps the case out of calibration use rather than filling the gap with an invented value."

### 3:00-3:45 - Input Readiness

1. Open **Input Readiness**.
2. Show the 31 report-defined input domains and sequential readiness funnel.
3. State: "Mapped and standardized are not the same as validated. Sol Ultra can prepare candidate observations and source links, but named specialists validate them."

### 3:45-4:30 - Evidence and fallback

1. Open **Evidence & Exports**, then **Calibration evidence**.
2. Show the reproducible run manifest and approval state.
3. Mention the generated Excel workbook and fit-gap assessment.
4. Close: "The value is an explainable chain from evidence readiness to a reproducible calculation to a human decision."

## Questions to handle carefully

- **What rate should government adopt?** The workbench does not determine a final rate. It tests configurations against explicit assumptions and a D5-approved envelope once available.
- **Does this prove incentives caused investment?** No. Additionality is a sensitivity assumption until comparator and counterfactual evidence is validated.
- **Is the nearest feasible configuration recommended?** No. It is the closest feasible tested configuration within the synthetic search grid.
- **Can Sol Ultra validate the evidence?** No. It can extract and organize candidate observations; legal, FBR, Finance, BOI, SEZA, model, and policy reviewers retain validation and decision authority.
- **Can this use confidential data?** Only in an approved environment with appropriate access controls and source authorization.

## Fallback files

- `outputs/sez_calibration_demo_outputs.xlsx`
- `docs/DATA_REQUIREMENTS_FIT_GAP.md`
- `docs/REMIT_DEMO_RUNBOOK.md`
