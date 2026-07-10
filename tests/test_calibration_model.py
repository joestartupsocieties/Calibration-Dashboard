from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sez_calibration.calibration_model import CalibrationAssumptions, simulate_enterprise, solve_revenue_neutral_parameter
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
        CalibrationAssumptions(annual_deduction_cap_pkr_m=999999.0, capex_deduction_rate=2.0),
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

    assert result["status"] == "entire_search_range_within_envelope"
    assert result["value"] == 2.0


def test_pipeline_writes_d6_workbook_sheets(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "config", tmp_path / "config")
    shutil.copytree(repo_root / "data" / "synthetic", tmp_path / "data" / "synthetic")

    result = run_pipeline(tmp_path)
    output_dir = result["output_dir"]

    assert (output_dir / "calibration_annual_enterprise.csv").stat().st_size > 0
    assert (output_dir / "calibration_portfolio_summary.csv").stat().st_size > 0
    assert (output_dir / "calibration_parameter_ranges.csv").stat().st_size > 0

    import openpyxl

    workbook = openpyxl.load_workbook(output_dir / "sez_calibration_demo_outputs.xlsx", read_only=True)
    expected_sheets = {
        "00_read_me",
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
