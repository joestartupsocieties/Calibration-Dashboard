from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sez_calibration.calibration_model import (
    CalibrationAssumptions,
    build_parameter_ranges,
    build_portfolio_summary,
    simulate_enterprise,
    solve_revenue_neutral_parameter,
)
from sez_calibration.export_outputs import run_pipeline


def enterprise(**overrides: object) -> pd.Series:
    data: dict[str, object] = {
        "enterprise_id": "E1",
        "zone_id": "Z1",
        "zone_name": "Synthetic Zone",
        "sector": "Manufacturing",
        "cohort_scope": "SEZ",
        "maturity_category": "operational",
        "aggregation_weight": 1.0,
        "compliance_status": "compliant",
        "pilot_cohort_flag": True,
        "baseline_assessed_income_pkr_m": 1000.0,
        "eligible_capex_pkr_m": 100.0,
        "eligible_rd_pkr_m": 20.0,
        "eligible_training_pkr_m": 10.0,
        "customs_exemption_pkr_m_cumulative": 50.0,
        "evidence_model_ready": True,
        "support_eligibility_status": "potential_cost_based_review_input_subject_to_validation",
        "developer_compliance_status": "compliant",
        "enterprise_compliance_status": "compliant",
        "legal_risk_level": "low",
        "fiscal_data_status": "validated",
        "additionality_confidence": "High",
    }
    data.update(overrides)
    return pd.Series(data)


def test_cost_based_formula_uses_incremental_deductions_and_never_negative_tax() -> None:
    assumptions = CalibrationAssumptions(
        statutory_cit_rate=0.29,
        ordinary_capex_depreciation_years=5,
        capex_deduction_rate=1.0,
        rd_super_deduction_total_rate=1.5,
        training_super_deduction_total_rate=1.5,
        utilization_rate=0.80,
        annual_deduction_cap_pkr_m=500,
        qualifying_expenditure_threshold_pkr_m=0,
    )

    rows = simulate_enterprise(enterprise(), assumptions, "cost_based_regime", "base")
    first_year = rows[0]

    assert first_year["ordinary_capex_depreciation_offset_pkr_m"] == 20.0
    assert first_year["capex_incremental_deduction_pkr_m"] == 80.0
    assert first_year["rd_incremental_deduction_pkr_m"] == 10.0
    assert first_year["training_incremental_deduction_pkr_m"] == 5.0
    assert first_year["deduction_generated_pkr_m"] == 76.0
    assert first_year["tax_due_pkr_m"] >= 0

    high_deduction_rows = simulate_enterprise(
        enterprise(eligible_capex_pkr_m=10000.0),
        CalibrationAssumptions(annual_deduction_cap_pkr_m=999999.0, capex_deduction_rate=2.0, qualifying_expenditure_threshold_pkr_m=0),
        "cost_based_regime",
        "base",
    )
    assert all(row["tax_due_pkr_m"] >= 0 for row in high_deduction_rows)


def test_status_quo_annualizes_cumulative_customs_only_in_schedule() -> None:
    rows = simulate_enterprise(
        enterprise(customs_exemption_pkr_m_cumulative=50.0),
        CalibrationAssumptions(status_quo_customs_annualization_years=5),
        "status_quo_to_2035",
        "base",
    )

    assert rows[0]["customs_expenditure_pkr_m"] == 10.0
    assert rows[4]["customs_expenditure_pkr_m"] == 10.0
    assert rows[5]["customs_expenditure_pkr_m"] == 0.0

    no_sez = simulate_enterprise(enterprise(customs_exemption_pkr_m_cumulative=50.0), CalibrationAssumptions(), "no_sez_specific_incentive", "base")
    assert all(row["customs_expenditure_pkr_m"] == 0.0 for row in no_sez)


def test_revenue_neutral_solver_returns_bounded_status() -> None:
    assumptions = CalibrationAssumptions()
    enterprises = pd.DataFrame([enterprise()])
    result = solve_revenue_neutral_parameter(
        enterprises,
        assumptions,
        "capex_deduction_rate",
        0.0,
        2.0,
        envelope=10_000_000.0,
        additionality_case="base",
    )

    assert result["status"] == "no_binding_upper_bound_identified_within_tested_range"
    assert result["value"] is None


def test_scenario_behavior_is_distinct_for_noncompliant_archetype() -> None:
    assumptions = CalibrationAssumptions(qualifying_expenditure_threshold_pkr_m=0)
    noncompliant = enterprise(
        compliance_status="non_compliant",
        developer_compliance_status="non_compliant",
        enterprise_compliance_status="partial",
        support_eligibility_status="not_support_ready_compliance_or_cure_required",
    )

    status = pd.DataFrame(simulate_enterprise(noncompliant, assumptions, "status_quo_to_2035", "base"))
    accelerated = pd.DataFrame(simulate_enterprise(noncompliant, assumptions, "accelerated_removal", "base"))

    assert accelerated["tax_collected_pkr_m"].sum() >= status["tax_collected_pkr_m"].sum()
    assert accelerated["gross_fiscal_cost_pkr_m"].sum() <= status["gross_fiscal_cost_pkr_m"].sum()


def test_combined_pilot_uptake_interpolates_consistently() -> None:
    ent = enterprise(pilot_cohort_flag=True)
    no_uptake = pd.DataFrame(
        simulate_enterprise(ent, CalibrationAssumptions(pilot_uptake_share=0.0, qualifying_expenditure_threshold_pkr_m=0), "combined_transition_pilot", "base")
    )
    half_uptake = pd.DataFrame(
        simulate_enterprise(ent, CalibrationAssumptions(pilot_uptake_share=0.5, qualifying_expenditure_threshold_pkr_m=0), "combined_transition_pilot", "base")
    )
    full_uptake = pd.DataFrame(
        simulate_enterprise(ent, CalibrationAssumptions(pilot_uptake_share=1.0, qualifying_expenditure_threshold_pkr_m=0), "combined_transition_pilot", "base")
    )
    non_pilot = pd.DataFrame(
        simulate_enterprise(ent, CalibrationAssumptions(qualifying_expenditure_threshold_pkr_m=0), "status_quo_to_2035", "base")
    )
    full_cost_based = pd.DataFrame(
        simulate_enterprise(ent, CalibrationAssumptions(qualifying_expenditure_threshold_pkr_m=0), "cost_based_regime", "base")
    )

    assert no_uptake["gross_fiscal_cost_pkr_m"].sum() == non_pilot["gross_fiscal_cost_pkr_m"].sum()
    assert full_uptake["gross_fiscal_cost_pkr_m"].sum() == full_cost_based["gross_fiscal_cost_pkr_m"].sum()
    assert full_uptake["gross_fiscal_cost_pkr_m"].sum() < half_uptake["gross_fiscal_cost_pkr_m"].sum() < no_uptake["gross_fiscal_cost_pkr_m"].sum()


def test_no_incentive_reference_receives_no_incentive_caused_additionality() -> None:
    rows = simulate_enterprise(enterprise(), CalibrationAssumptions(qualifying_expenditure_threshold_pkr_m=0), "no_sez_specific_incentive", "high")
    assert all(row["incremental_assessed_income_pkr_m"] == 0 for row in rows)


def test_cost_based_incremental_income_requires_positive_available_incentive() -> None:
    ent = enterprise(
        baseline_assessed_income_pkr_m=10_000.0,
        eligible_capex_pkr_m=5_000.0,
        eligible_rd_pkr_m=0.0,
        eligible_training_pkr_m=0.0,
    )
    no_rate = pd.DataFrame(
        simulate_enterprise(
            ent,
            CalibrationAssumptions(
                instrument_package="capex_only",
                capex_deduction_rate=0.0,
                annual_deduction_cap_pkr_m=10_000.0,
                utilization_rate=1.0,
                qualifying_expenditure_threshold_pkr_m=0.0,
            ),
            "cost_based_regime",
            "high",
        )
    )
    no_cap = pd.DataFrame(
        simulate_enterprise(
            ent,
            CalibrationAssumptions(
                instrument_package="capex_only",
                capex_deduction_rate=1.25,
                annual_deduction_cap_pkr_m=0.0,
                utilization_rate=1.0,
                qualifying_expenditure_threshold_pkr_m=0.0,
            ),
            "cost_based_regime",
            "high",
        )
    )
    no_utilization = pd.DataFrame(
        simulate_enterprise(
            ent,
            CalibrationAssumptions(
                instrument_package="capex_only",
                capex_deduction_rate=1.25,
                annual_deduction_cap_pkr_m=10_000.0,
                utilization_rate=0.0,
                qualifying_expenditure_threshold_pkr_m=0.0,
            ),
            "cost_based_regime",
            "high",
        )
    )
    threshold_blocks = pd.DataFrame(
        simulate_enterprise(
            ent,
            CalibrationAssumptions(
                instrument_package="capex_only",
                capex_deduction_rate=1.25,
                annual_deduction_cap_pkr_m=10_000.0,
                utilization_rate=1.0,
                qualifying_expenditure_threshold_pkr_m=999_999.0,
            ),
            "cost_based_regime",
            "high",
        )
    )
    positive = pd.DataFrame(
        simulate_enterprise(
            ent,
            CalibrationAssumptions(
                instrument_package="capex_only",
                capex_deduction_rate=1.25,
                annual_deduction_cap_pkr_m=10_000.0,
                utilization_rate=1.0,
                qualifying_expenditure_threshold_pkr_m=0.0,
            ),
            "cost_based_regime",
            "high",
        )
    )

    for blocked in [no_rate, no_cap, no_utilization, threshold_blocks]:
        assert blocked["potential_incentive_deduction_pkr_m"].sum() == 0
        assert blocked["incentive_intensity_factor"].sum() == 0
        assert blocked["incremental_assessed_income_pkr_m"].sum() == 0
    assert positive["potential_incentive_deduction_pkr_m"].sum() > 0
    assert positive["incremental_assessed_income_pkr_m"].sum() > 0


def test_parameter_controls_change_results_when_relevant() -> None:
    ent = pd.Series(
        enterprise(
            baseline_assessed_income_pkr_m=50_000.0,
            eligible_capex_pkr_m=10_000.0,
            eligible_rd_pkr_m=1_000.0,
            eligible_training_pkr_m=500.0,
        )
    )
    low_rate = pd.DataFrame(
        simulate_enterprise(ent, CalibrationAssumptions(capex_deduction_rate=0.25, annual_deduction_cap_pkr_m=50_000, qualifying_expenditure_threshold_pkr_m=0), "cost_based_regime", "base")
    )
    high_rate = pd.DataFrame(
        simulate_enterprise(ent, CalibrationAssumptions(capex_deduction_rate=1.25, annual_deduction_cap_pkr_m=50_000, qualifying_expenditure_threshold_pkr_m=0), "cost_based_regime", "base")
    )
    low_cap = pd.DataFrame(
        simulate_enterprise(ent, CalibrationAssumptions(capex_deduction_rate=1.25, annual_deduction_cap_pkr_m=500, qualifying_expenditure_threshold_pkr_m=0), "cost_based_regime", "base")
    )
    high_cap = pd.DataFrame(
        simulate_enterprise(ent, CalibrationAssumptions(capex_deduction_rate=1.25, annual_deduction_cap_pkr_m=50_000, qualifying_expenditure_threshold_pkr_m=0), "cost_based_regime", "base")
    )
    capex_only = pd.DataFrame(
        simulate_enterprise(ent, CalibrationAssumptions(instrument_package="capex_only", annual_deduction_cap_pkr_m=50_000, qualifying_expenditure_threshold_pkr_m=0), "cost_based_regime", "base")
    )
    rd_training = pd.DataFrame(
        simulate_enterprise(ent, CalibrationAssumptions(instrument_package="rd_training", annual_deduction_cap_pkr_m=50_000, qualifying_expenditure_threshold_pkr_m=0), "cost_based_regime", "base")
    )
    threshold_blocks = pd.DataFrame(
        simulate_enterprise(ent, CalibrationAssumptions(qualifying_expenditure_threshold_pkr_m=99_999), "cost_based_regime", "base")
    )

    assert high_rate["gross_fiscal_cost_pkr_m"].sum() > low_rate["gross_fiscal_cost_pkr_m"].sum()
    assert high_cap["gross_fiscal_cost_pkr_m"].sum() > low_cap["gross_fiscal_cost_pkr_m"].sum()
    assert capex_only["gross_fiscal_cost_pkr_m"].sum() != rd_training["gross_fiscal_cost_pkr_m"].sum()
    assert threshold_blocks["deduction_generated_pkr_m"].sum() == 0
    assert threshold_blocks["incremental_assessed_income_pkr_m"].sum() == 0


def test_fiscal_identities_and_carryforward_reconcile() -> None:
    rows = pd.DataFrame(
        simulate_enterprise(
            enterprise(baseline_assessed_income_pkr_m=400.0, eligible_capex_pkr_m=5_000.0),
            CalibrationAssumptions(capex_deduction_rate=1.25, annual_deduction_cap_pkr_m=10_000, qualifying_expenditure_threshold_pkr_m=0),
            "cost_based_regime",
            "base",
        )
    )

    tax_expenditure_identity = rows["benchmark_tax_liability_pkr_m"] - rows["tax_collected_pkr_m"]
    assert (rows["tax_expenditure_pkr_m"] - tax_expenditure_identity).abs().max() < 1e-3
    assert (rows["cash_net_revenue_pkr_m"] - (rows["tax_collected_pkr_m"] - rows["incremental_admin_cost_pkr_m"] - rows["other_government_cash_cost_pkr_m"])).abs().max() < 1e-3
    assert rows["tax_due_pkr_m"].min() >= 0
    assert rows["closing_carryforward_pkr_m"].max() >= 0


def test_frontier_outputs_scale_by_pilot_uptake() -> None:
    assumptions = CalibrationAssumptions(
        capex_deduction_rate=1.25,
        annual_deduction_cap_pkr_m=25_000.0,
        qualifying_expenditure_threshold_pkr_m=0.0,
        utilization_rate=0.8,
        d5_fiscal_envelope_pkr_m=10_000_000.0,
    )
    frontier = build_parameter_ranges(
        pd.DataFrame(
            [
                enterprise(
                    baseline_assessed_income_pkr_m=50_000.0,
                    eligible_capex_pkr_m=10_000.0,
                    eligible_rd_pkr_m=1_000.0,
                    eligible_training_pkr_m=500.0,
                )
            ]
        ),
        assumptions,
    )
    subset = frontier[
        frontier["additionality_case"].eq("base")
        & frontier["instrument_package"].eq("full")
        & frontier["capex_deduction_rate"].eq(1.25)
        & frontier["annual_cap_pkr_m"].eq(25_000.0)
        & frontier["qualifying_threshold_pkr_m"].eq(0.0)
    ].set_index("pilot_uptake_share")

    assert subset.loc[0.0, "npv_tested_fiscal_cost_pkr_m"] == 0
    assert subset.loc[0.0, "npv_incremental_assessed_income_pkr_m"] == 0
    assert subset.loc[0.0, "review_workload_hours"] == 0
    assert abs(subset.loc[0.6, "npv_tested_fiscal_cost_pkr_m"] - subset.loc[1.0, "npv_tested_fiscal_cost_pkr_m"] * 0.6) < 1e-3
    assert abs(subset.loc[0.6, "npv_incremental_assessed_income_pkr_m"] - subset.loc[1.0, "npv_incremental_assessed_income_pkr_m"] * 0.6) < 1e-3
    assert abs(subset.loc[0.6, "review_workload_hours"] - subset.loc[1.0, "review_workload_hours"] * 0.6) < 1e-3


def test_portfolio_fte_uses_annual_workload_not_total_projection_hours() -> None:
    assumptions = CalibrationAssumptions(annual_fte_hours=100.0, qualifying_expenditure_threshold_pkr_m=0.0)
    annual = pd.DataFrame(
        simulate_enterprise(
            enterprise(
                baseline_assessed_income_pkr_m=10_000.0,
                eligible_capex_pkr_m=5_000.0,
            ),
            assumptions,
            "cost_based_regime",
            "base",
        )
    )
    summary = build_portfolio_summary(annual, assumptions)
    row = summary[summary["scenario_id"].eq("cost_based_regime") & summary["additionality_case"].eq("base")].iloc[0]
    weighted_annual_hours = annual["admin_review_hours"] * annual["aggregation_weight"]
    peak_hours = pd.DataFrame({"year": annual["fiscal_year"], "hours": weighted_annual_hours}).groupby("year")["hours"].sum().max()

    assert row["review_workload_hours"] == round(weighted_annual_hours.sum(), 4)
    assert row["peak_annual_review_workload_hours"] == round(peak_hours, 4)
    assert row["indicative_fte_requirement"] == round(peak_hours / assumptions.annual_fte_hours, 6)


def test_pipeline_writes_d6_workbook_sheets(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "config", tmp_path / "config")
    shutil.copytree(repo_root / "data" / "synthetic", tmp_path / "data" / "synthetic")

    result = run_pipeline(tmp_path)
    output_dir = result["output_dir"]

    assert (output_dir / "calibration_annual_enterprise.csv").stat().st_size > 0
    assert (output_dir / "calibration_portfolio_summary.csv").stat().st_size > 0
    assert (output_dir / "calibration_parameter_ranges.csv").stat().st_size > 0
    assert (output_dir / "calibration_input_register.csv").stat().st_size > 0
    assert (output_dir / "calibration_run_manifest.csv").stat().st_size > 0
    register = result["frames"]["calibration_input_register"]
    assert len(register) == 31
    assert set(register["demo_coverage_status"]) == {
        "Demonstrated",
        "Partially demonstrated",
        "Workflow demonstrated",
        "Not demonstrated",
    }
    assert "VALIDATED" not in set(register["current_workflow_status"])
    manifest = result["frames"]["calibration_run_manifest"]
    assert manifest.loc[0, "run_id"].startswith("RUN-")
    assert manifest.loc[0, "approval_state"] == "NOT_SUBMITTED - human review required"
    assert manifest.loc[0, "publication_state"] == "SYNTHETIC_DEMO_ONLY"
    frontier = result["frames"]["calibration_parameter_ranges"]
    assert frontier["feasible_flag"].astype(bool).any()
    assert (~frontier["feasible_flag"].astype(bool)).any()

    import openpyxl

    workbook = openpyxl.load_workbook(output_dir / "sez_calibration_demo_outputs.xlsx", read_only=True)
    expected_sheets = {
        "00_read_me",
        "01_input_register",
        "02_run_manifest",
        "02_model_assumptions",
        "03_scenario_definitions",
        "04_annual_enterprise",
        "06_portfolio_summary",
        "08_parameter_ranges",
        "09_verification_rules",
        "14_d7_handoff",
    }
    assert expected_sheets.issubset(set(workbook.sheetnames))


def test_d6_parameter_override_changes_pipeline_output(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "config", tmp_path / "config")
    shutil.copytree(repo_root / "data" / "synthetic", tmp_path / "data" / "synthetic")

    low_cap = run_pipeline(tmp_path, scenario={"d6_annual_deduction_cap_pkr_m": 0.0}, write_outputs=False)
    high_cap = run_pipeline(tmp_path, scenario={"d6_annual_deduction_cap_pkr_m": 1000.0}, write_outputs=False)

    def cost(result: dict[str, object]) -> float:
        portfolio = result["frames"]["calibration_portfolio_summary"]
        row = portfolio[
            portfolio["scenario_id"].eq("cost_based_regime")
            & portfolio["additionality_case"].eq("base")
        ].iloc[0]
        return float(row["npv_gross_fiscal_cost_pkr_m"])

    assert cost(high_cap) != cost(low_cap)
