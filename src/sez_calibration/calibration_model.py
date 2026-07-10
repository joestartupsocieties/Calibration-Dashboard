from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pandas as pd

from .utils import clean_text, safe_divide, to_float


MODEL_VERSION = "d6-thin-slice-v0.1"
YEARS = list(range(2026, 2036))
SCENARIOS = {
    "status_quo_to_2035": "Status quo to 2035",
    "accelerated_removal": "Accelerated removal for non-compliant zones/enterprises",
    "cost_based_regime": "Cost-based regime",
    "combined_transition_pilot": "Combined transition plus pilot",
    "no_sez_specific_incentive": "No SEZ-specific incentive reference",
}
ADDITIONALITY_CASES = ("low", "base", "high")


@dataclass(frozen=True)
class CalibrationAssumptions:
    fx_pkr_per_usd: float = 280.0
    statutory_cit_rate: float = 0.29
    discount_rate: float = 0.12
    projection_start_year: int = 2026
    projection_end_year: int = 2035
    current_holiday_exemption_share: float = 1.0
    holiday_expiry_year: int = 2035
    assessed_income_growth: float = 0.03
    eligible_expenditure_growth: float = 0.02
    ordinary_capex_depreciation_years: int = 5
    capex_deduction_rate: float = 1.0
    rd_super_deduction_total_rate: float = 1.5
    training_super_deduction_total_rate: float = 1.5
    utilization_rate: float = 0.80
    annual_deduction_cap_pkr_m: float = 350.0
    carry_forward_years: int = 3
    additionality_low: float = 0.10
    additionality_base: float = 0.25
    additionality_high: float = 0.40
    taxable_return_on_incremental_expenditure: float = 0.18
    additionality_income_lag_years: int = 1
    admin_cost_per_enterprise_pkr_m: float = 2.0
    status_quo_customs_annualization_years: int = 5
    d5_fiscal_envelope_pkr_m: float | None = None
    pilot_uptake_share: float = 0.60
    cohort_eligibility_policy: str = "unresolved"

    def additionality_share(self, case: str) -> float:
        return {
            "low": self.additionality_low,
            "base": self.additionality_base,
            "high": self.additionality_high,
        }.get(case, self.additionality_base)


def run_calibration_model(
    project_root: Path,
    zones: pd.DataFrame,
    recommendations: pd.DataFrame,
    data_profile: str = "synthetic",
    scenario: dict[str, Any] | None = None,
) -> dict[str, pd.DataFrame]:
    scenario = scenario or {}
    data_dir = Path(project_root) / "data"
    profile_dir = data_dir / "synthetic" if data_profile == "synthetic" else data_dir
    enterprise_path = profile_dir / "synthetic_enterprise_summary.csv"
    assumptions_path = profile_dir / "synthetic_calibration_assumptions.csv"
    weights_path = profile_dir / "synthetic_enterprise_weights.csv"
    verification_path = profile_dir / "synthetic_verification_requirements.csv"

    assumptions_frame = _load_assumptions_frame(assumptions_path)
    assumptions = _assumptions_from_frame(assumptions_frame)
    assumptions = _assumptions_with_ui_overrides(assumptions, scenario)
    assumptions_frame = _assumptions_frame_with_overrides(assumptions_frame, assumptions, scenario)
    scenario_definitions = build_scenario_definitions(assumptions)
    verification = _load_verification_requirements(verification_path)

    if not enterprise_path.exists():
        status = "missing_enterprise_data_blocked" if data_profile != "synthetic" else "synthetic_enterprise_data_missing"
        return _blocked_frames(status, assumptions_frame, scenario_definitions, verification)

    enterprises_raw = pd.read_csv(enterprise_path)
    weights = _load_weights(weights_path)
    enterprises = prepare_enterprise_inputs(enterprises_raw, weights, zones, recommendations, assumptions)
    readiness = build_model_readiness(enterprises)
    model_ready = enterprises[enterprises["model_ready"].astype(bool)].copy()

    if model_ready.empty:
        return _blocked_frames("no_gate_cleared_enterprises", assumptions_frame, scenario_definitions, verification, enterprises, readiness)

    annual = build_annual_results(model_ready, assumptions)
    zone_aggregation = build_zone_aggregation(annual)
    portfolio_summary = build_portfolio_summary(annual, assumptions)
    sensitivity = build_sensitivity(model_ready, assumptions)
    parameter_ranges = build_parameter_ranges(model_ready, assumptions)
    reconciliation = build_reconciliation(enterprises, zones, assumptions)
    d7_handoff = build_d7_handoff(parameter_ranges, verification, assumptions)
    excluded = enterprises[~enterprises["model_ready"].astype(bool)].copy()

    return {
        "calibration_enterprise_inputs": enterprises,
        "calibration_assumptions": assumptions_frame,
        "calibration_scenario_definitions": scenario_definitions,
        "calibration_annual_enterprise": annual,
        "calibration_zone_aggregation": zone_aggregation,
        "calibration_portfolio_summary": portfolio_summary,
        "calibration_sensitivity": sensitivity,
        "calibration_parameter_ranges": parameter_ranges,
        "calibration_verification_rules": verification,
        "calibration_d7_handoff": d7_handoff,
        "calibration_reconciliation": reconciliation,
        "calibration_model_readiness": readiness,
        "calibration_excluded_records": excluded,
    }


def prepare_enterprise_inputs(
    enterprises_raw: pd.DataFrame,
    weights: pd.DataFrame,
    zones: pd.DataFrame,
    recommendations: pd.DataFrame,
    assumptions: CalibrationAssumptions,
) -> pd.DataFrame:
    df = enterprises_raw.copy()
    for col in df.columns:
        if col.endswith(("_usd_m", "_pkr_m", "_pkr_m_2026", "_pkr_m_cumulative")) or col in {
            "employment_actual",
            "tax_paid_pkr_m_2026",
            "cit_foregone_pkr_m_2026",
            "customs_exemption_pkr_m_cumulative",
        }:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.merge(weights, on=["enterprise_id", "zone_id"], how="left")
    df["aggregation_weight"] = pd.to_numeric(df.get("aggregation_weight"), errors="coerce").fillna(1.0)
    df["cohort_scope"] = df.get("cohort_scope", "SEZ").fillna("SEZ").astype(str)
    df["pilot_cohort_flag"] = df.get("pilot_cohort_flag", False).apply(_to_bool)
    df["maturity_category"] = df.get("maturity_category", "").fillna("").astype(str)
    df["fx_pkr_per_usd"] = assumptions.fx_pkr_per_usd

    usd_fields = ["investment_actual_usd_m", "exports_usd_m_2026", "domestic_sales_usd_m_2026", "capex_eligible_usd_m", "rd_spend_usd_m", "training_spend_usd_m"]
    for field in usd_fields:
        if field in df.columns:
            df[f"{field.replace('_usd_m', '')}_pkr_m"] = pd.to_numeric(df[field], errors="coerce") * assumptions.fx_pkr_per_usd

    df["ordinary_benchmark_tax_pkr_m_2026"] = df[["cit_foregone_pkr_m_2026", "tax_paid_pkr_m_2026"]].sum(axis=1, min_count=1)
    df["baseline_assessed_income_pkr_m"] = df["ordinary_benchmark_tax_pkr_m_2026"] / assumptions.statutory_cit_rate
    df["eligible_capex_pkr_m"] = df["capex_eligible_pkr_m"].fillna(0.0)
    df["eligible_rd_pkr_m"] = df["rd_spend_pkr_m"].fillna(0.0)
    df["eligible_training_pkr_m"] = df["training_spend_pkr_m"].fillna(0.0)

    rec_cols = [
        "zone_id",
        "legal_risk_level",
        "fiscal_data_status",
        "fiscal_exposure_level",
        "developer_compliance_status",
        "enterprise_compliance_status",
        "data_confidence_band",
        "activity_category",
        "recommended_treatment",
        "hard_gates_triggered",
    ]
    rec = recommendations[[c for c in rec_cols if c in recommendations.columns]].drop_duplicates("zone_id")
    df = df.merge(rec, on="zone_id", how="left", suffixes=("", "_triage"))

    df["legal_ready"] = df["legal_risk_level"].fillna("").astype(str).str.lower().isin(["low"])
    df["fiscal_ready"] = df["fiscal_data_status"].fillna("").astype(str).str.lower().isin(["validated", "verified"])
    df["compliance_ready"] = (
        df.get("compliance_status", "").fillna("").astype(str).str.lower().eq("compliant")
        & df["developer_compliance_status"].fillna("").astype(str).str.lower().eq("compliant")
        & df["enterprise_compliance_status"].fillna("").astype(str).str.lower().eq("compliant")
    )
    df["record_quality_status"] = df["data_confidence_band"].fillna("not assessed")
    df["substantive_evidence_status"] = "synthetic/unvalidated"
    df["epz_excluded"] = df["cohort_scope"].str.upper().eq("EPZ")
    df["model_ready"] = df["legal_ready"] & df["fiscal_ready"] & df["compliance_ready"] & ~df["epz_excluded"] & df["baseline_assessed_income_pkr_m"].notna()
    df["blocked_reason"] = df.apply(_blocked_reason, axis=1)
    df["model_version"] = MODEL_VERSION
    return df


def build_model_readiness(enterprises: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "enterprise_id",
        "zone_id",
        "zone_name",
        "cohort_scope",
        "maturity_category",
        "legal_ready",
        "fiscal_ready",
        "compliance_ready",
        "record_quality_status",
        "substantive_evidence_status",
        "model_ready",
        "blocked_reason",
    ]
    return enterprises[[c for c in cols if c in enterprises.columns]].copy()


def build_annual_results(enterprises: pd.DataFrame, assumptions: CalibrationAssumptions) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for additionality_case in ADDITIONALITY_CASES:
        for scenario_id in SCENARIOS:
            for _, enterprise in enterprises.iterrows():
                rows.extend(simulate_enterprise(enterprise, assumptions, scenario_id, additionality_case))
    return pd.DataFrame(rows)


def simulate_enterprise(
    enterprise: pd.Series | dict[str, Any],
    assumptions: CalibrationAssumptions,
    scenario_id: str,
    additionality_case: str = "base",
) -> list[dict[str, Any]]:
    carryforward: list[dict[str, float | int]] = []
    rows: list[dict[str, Any]] = []
    base_income = _num(enterprise, "baseline_assessed_income_pkr_m")
    capex_base = _num(enterprise, "eligible_capex_pkr_m")
    rd_base = _num(enterprise, "eligible_rd_pkr_m")
    training_base = _num(enterprise, "eligible_training_pkr_m")
    customs_cumulative = _num(enterprise, "customs_exemption_pkr_m_cumulative")
    indirect_base = _num(enterprise, "public_infrastructure_cost_pkr_m") + _num(enterprise, "land_concession_pkr_m")
    additionality_share = assumptions.additionality_share(additionality_case)

    for year in YEARS:
        n = year - assumptions.projection_start_year
        discount_factor = 1 / ((1 + assumptions.discount_rate) ** n)
        assessed_income = base_income * ((1 + assumptions.assessed_income_growth) ** n)
        capex = capex_base * ((1 + assumptions.eligible_expenditure_growth) ** n)
        rd = rd_base * ((1 + assumptions.eligible_expenditure_growth) ** n)
        training = training_base * ((1 + assumptions.eligible_expenditure_growth) ** n)
        qualifying_expenditure = capex + rd + training
        lag_n = n - assumptions.additionality_income_lag_years
        prior_expenditure = 0.0 if lag_n < 0 else (capex_base + rd_base + training_base) * ((1 + assumptions.eligible_expenditure_growth) ** lag_n)
        incremental_income = prior_expenditure * additionality_share * assumptions.taxable_return_on_incremental_expenditure
        benchmark_income = assessed_income + incremental_income
        benchmark_tax = max(0.0, benchmark_income * assumptions.statutory_cit_rate)

        deduction_generated = deduction_used = carryforward_used = expired = closing_carryforward = 0.0
        capex_incremental = rd_incremental = training_incremental = ordinary_capex_offset = 0.0
        tax_due = benchmark_tax
        direct_cit_expenditure = 0.0
        customs_expenditure = 0.0
        admin_cost = 0.0
        state = "Full CIT after 2035 with no SEZ-specific incentive"

        if scenario_id == "no_sez_specific_incentive":
            state = "Full CIT / no SEZ-specific incentive reference"
        elif scenario_id == "status_quo_to_2035":
            state = "Current CIT holiday/protected treatment"
            if year <= assumptions.holiday_expiry_year:
                protected_share = assumptions.current_holiday_exemption_share
                tax_due = benchmark_tax * (1 - protected_share)
            direct_cit_expenditure = max(0.0, benchmark_tax - tax_due)
            customs_expenditure = _annualized_customs(customs_cumulative, year, assumptions)
        elif scenario_id == "accelerated_removal":
            state = "Accelerated removal for non-compliant zones/enterprises"
            non_compliant = clean_text(enterprise.get("compliance_status")).lower() != "compliant"
            if non_compliant:
                tax_due = benchmark_tax
            elif year <= assumptions.holiday_expiry_year:
                tax_due = benchmark_tax * (1 - assumptions.current_holiday_exemption_share)
            direct_cit_expenditure = max(0.0, benchmark_tax - tax_due)
            customs_expenditure = _annualized_customs(customs_cumulative, year, assumptions) if not non_compliant else 0.0
        elif scenario_id == "cost_based_regime":
            state = "Proposed CIT phase-in plus temporary cost-based deductions"
            tax_due, deduction_data, carryforward = _apply_cost_based_deductions(
                benchmark_income, benchmark_tax, capex, rd, training, carryforward, assumptions, year
            )
            deduction_generated = deduction_data["deduction_generated_pkr_m"]
            deduction_used = deduction_data["deduction_used_pkr_m"]
            carryforward_used = deduction_data["carryforward_used_pkr_m"]
            expired = deduction_data["deduction_expired_pkr_m"]
            closing_carryforward = deduction_data["closing_carryforward_pkr_m"]
            capex_incremental = deduction_data["capex_incremental_deduction_pkr_m"]
            rd_incremental = deduction_data["rd_incremental_deduction_pkr_m"]
            training_incremental = deduction_data["training_incremental_deduction_pkr_m"]
            ordinary_capex_offset = deduction_data["ordinary_capex_depreciation_offset_pkr_m"]
            direct_cit_expenditure = max(0.0, benchmark_tax - tax_due)
            admin_cost = assumptions.admin_cost_per_enterprise_pkr_m
        elif scenario_id == "combined_transition_pilot":
            state = "Combined transition plus pilot"
            pilot_applies = _to_bool(enterprise.get("pilot_cohort_flag")) and assumptions.pilot_uptake_share > 0
            if pilot_applies:
                tax_due, deduction_data, carryforward = _apply_cost_based_deductions(
                    benchmark_income, benchmark_tax, capex, rd, training, carryforward, assumptions, year
                )
                deduction_generated = deduction_data["deduction_generated_pkr_m"] * assumptions.pilot_uptake_share
                deduction_used = deduction_data["deduction_used_pkr_m"] * assumptions.pilot_uptake_share
                carryforward_used = deduction_data["carryforward_used_pkr_m"] * assumptions.pilot_uptake_share
                expired = deduction_data["deduction_expired_pkr_m"] * assumptions.pilot_uptake_share
                closing_carryforward = deduction_data["closing_carryforward_pkr_m"] * assumptions.pilot_uptake_share
                capex_incremental = deduction_data["capex_incremental_deduction_pkr_m"] * assumptions.pilot_uptake_share
                rd_incremental = deduction_data["rd_incremental_deduction_pkr_m"] * assumptions.pilot_uptake_share
                training_incremental = deduction_data["training_incremental_deduction_pkr_m"] * assumptions.pilot_uptake_share
                ordinary_capex_offset = deduction_data["ordinary_capex_depreciation_offset_pkr_m"] * assumptions.pilot_uptake_share
                direct_cit_expenditure = max(0.0, benchmark_tax - tax_due)
                admin_cost = assumptions.admin_cost_per_enterprise_pkr_m
            else:
                tax_due = benchmark_tax
                direct_cit_expenditure = 0.0

        tax_due = max(0.0, tax_due)
        indirect_cost = indirect_base / len(YEARS)
        gross_fiscal_cost = direct_cit_expenditure + customs_expenditure + admin_cost + indirect_cost
        net_fiscal_position = tax_due - gross_fiscal_cost
        after_tax_income = benchmark_income - tax_due
        weight = _num(enterprise, "aggregation_weight", 1.0)

        rows.append(
            {
                "enterprise_id": enterprise.get("enterprise_id"),
                "zone_id": enterprise.get("zone_id"),
                "zone_name": enterprise.get("zone_name"),
                "sector": enterprise.get("sector"),
                "cohort_scope": enterprise.get("cohort_scope"),
                "maturity_category": enterprise.get("maturity_category"),
                "aggregation_weight": weight,
                "scenario_id": scenario_id,
                "scenario": SCENARIOS[scenario_id],
                "enterprise_tax_state": state,
                "additionality_case": additionality_case,
                "fiscal_year": year,
                "assessed_income_before_relief_pkr_m": round(benchmark_income, 4),
                "additionality_share": additionality_share,
                "incremental_assessed_income_pkr_m": round(incremental_income, 4),
                "benchmark_tax_no_sez_pkr_m": round(benchmark_tax, 4),
                "tax_due_pkr_m": round(tax_due, 4),
                "tax_collected_pkr_m": round(tax_due, 4),
                "effective_tax_rate": round(safe_divide(tax_due, benchmark_income) or 0.0, 6),
                "eligible_capex_pkr_m": round(capex, 4),
                "eligible_rd_pkr_m": round(rd, 4),
                "eligible_training_pkr_m": round(training, 4),
                "capex_incremental_deduction_pkr_m": round(capex_incremental, 4),
                "ordinary_capex_depreciation_offset_pkr_m": round(ordinary_capex_offset, 4),
                "rd_incremental_deduction_pkr_m": round(rd_incremental, 4),
                "training_incremental_deduction_pkr_m": round(training_incremental, 4),
                "deduction_generated_pkr_m": round(deduction_generated, 4),
                "deduction_used_pkr_m": round(deduction_used, 4),
                "carryforward_used_pkr_m": round(carryforward_used, 4),
                "deduction_expired_pkr_m": round(expired, 4),
                "closing_carryforward_pkr_m": round(closing_carryforward, 4),
                "direct_cit_expenditure_pkr_m": round(direct_cit_expenditure, 4),
                "customs_expenditure_pkr_m": round(customs_expenditure, 4),
                "incremental_admin_cost_pkr_m": round(admin_cost, 4),
                "indirect_cost_allocated_pkr_m": round(indirect_cost, 4),
                "gross_fiscal_cost_pkr_m": round(gross_fiscal_cost, 4),
                "net_fiscal_position_pkr_m": round(net_fiscal_position, 4),
                "after_tax_income_pkr_m": round(after_tax_income, 4),
                "discount_factor": round(discount_factor, 8),
                "npv_gross_fiscal_cost_pkr_m": round(gross_fiscal_cost * discount_factor, 4),
                "npv_net_fiscal_position_pkr_m": round(net_fiscal_position * discount_factor, 4),
                "weighted_gross_fiscal_cost_pkr_m": round(gross_fiscal_cost * weight, 4),
                "weighted_tax_collected_pkr_m": round(tax_due * weight, 4),
                "weighted_after_tax_income_pkr_m": round(after_tax_income * weight, 4),
                "model_version": MODEL_VERSION,
                "formula_reference": "docs/D6_MODEL_METHOD.md",
            }
        )
    return rows


def _apply_cost_based_deductions(
    benchmark_income: float,
    benchmark_tax: float,
    capex: float,
    rd: float,
    training: float,
    carryforward: list[dict[str, float | int]],
    assumptions: CalibrationAssumptions,
    year: int,
) -> tuple[float, dict[str, float], list[dict[str, float | int]]]:
    carryforward, expired = _expire_carryforward(carryforward, year)
    ordinary_offset = capex / max(assumptions.ordinary_capex_depreciation_years, 1)
    capex_incremental = max(0.0, capex * assumptions.capex_deduction_rate - ordinary_offset)
    rd_incremental = max(0.0, rd * (assumptions.rd_super_deduction_total_rate - 1.0))
    training_incremental = max(0.0, training * (assumptions.training_super_deduction_total_rate - 1.0))
    generated_before_utilization = capex_incremental + rd_incremental + training_incremental
    generated = min(generated_before_utilization * assumptions.utilization_rate, assumptions.annual_deduction_cap_pkr_m)
    current_entry = {"amount": generated, "expiry_year": year + assumptions.carry_forward_years, "origin_year": year}
    available_entries = carryforward + ([current_entry] if generated > 0 else [])
    used, carryforward_used, updated_entries = _use_carryforward_fifo(available_entries, benchmark_income, year)
    taxable_income_after_deduction = max(0.0, benchmark_income - used)
    phase_rate = assumptions.statutory_cit_rate * _cit_phase_in_factor(year, assumptions)
    tax_due = max(0.0, taxable_income_after_deduction * phase_rate)
    closing = sum(float(entry["amount"]) for entry in updated_entries)
    return tax_due, {
        "capex_incremental_deduction_pkr_m": capex_incremental,
        "ordinary_capex_depreciation_offset_pkr_m": ordinary_offset,
        "rd_incremental_deduction_pkr_m": rd_incremental,
        "training_incremental_deduction_pkr_m": training_incremental,
        "deduction_generated_pkr_m": generated,
        "deduction_used_pkr_m": used,
        "carryforward_used_pkr_m": carryforward_used,
        "deduction_expired_pkr_m": expired,
        "closing_carryforward_pkr_m": closing,
    }, updated_entries


def build_zone_aggregation(annual: pd.DataFrame) -> pd.DataFrame:
    if annual.empty:
        return pd.DataFrame()
    df = annual.copy()
    for col in ["gross_fiscal_cost_pkr_m", "tax_collected_pkr_m", "after_tax_income_pkr_m", "npv_gross_fiscal_cost_pkr_m", "npv_net_fiscal_position_pkr_m"]:
        df[f"weighted_{col}"] = df[col] * df["aggregation_weight"]
    group_cols = ["zone_id", "zone_name", "scenario_id", "scenario", "additionality_case", "fiscal_year"]
    value_cols = [c for c in df.columns if c.startswith("weighted_")]
    out = df.groupby(group_cols, as_index=False)[value_cols].sum()
    out["model_version"] = MODEL_VERSION
    return out


def build_portfolio_summary(annual: pd.DataFrame, assumptions: CalibrationAssumptions) -> pd.DataFrame:
    if annual.empty:
        return pd.DataFrame()
    df = annual.copy()
    group_cols = ["scenario_id", "scenario", "additionality_case"]
    rows = []
    for keys, group in df.groupby(group_cols):
        scenario_id, scenario, additionality_case = keys
        weighted_cost_npv = (group["gross_fiscal_cost_pkr_m"] * group["aggregation_weight"] * group["discount_factor"]).sum()
        weighted_tax_npv = (group["tax_collected_pkr_m"] * group["aggregation_weight"] * group["discount_factor"]).sum()
        weighted_after_tax_npv = (group["after_tax_income_pkr_m"] * group["aggregation_weight"] * group["discount_factor"]).sum()
        rows.append(
            {
                "scenario_id": scenario_id,
                "scenario": scenario,
                "additionality_case": additionality_case,
                "npv_gross_fiscal_cost_pkr_m": round(weighted_cost_npv, 4),
                "npv_tax_collected_pkr_m": round(weighted_tax_npv, 4),
                "npv_enterprise_after_tax_income_pkr_m": round(weighted_after_tax_npv, 4),
                "npv_net_fiscal_position_pkr_m": round(weighted_tax_npv - weighted_cost_npv, 4),
                "fiscal_envelope_type": "synthetic_proxy_status_quo" if assumptions.d5_fiscal_envelope_pkr_m is None else "D5_envelope_user_supplied",
                "fiscal_envelope_pkr_m": round(_fiscal_envelope(df, assumptions), 4),
                "model_version": MODEL_VERSION,
            }
        )
    return pd.DataFrame(rows)


def build_sensitivity(enterprises: pd.DataFrame, assumptions: CalibrationAssumptions) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for case in ADDITIONALITY_CASES:
        annual = pd.DataFrame(
            row
            for _, enterprise in enterprises.iterrows()
            for row in simulate_enterprise(enterprise, assumptions, "cost_based_regime", case)
        )
        summary = build_portfolio_summary(annual, assumptions)
        row = summary.iloc[0].to_dict()
        row["sensitivity_axis"] = "additionality"
        row["sensitivity_value"] = case
        rows.append(row)
    for rate in [max(0, assumptions.capex_deduction_rate - 0.25), assumptions.capex_deduction_rate, assumptions.capex_deduction_rate + 0.25]:
        variant = replace(assumptions, capex_deduction_rate=rate)
        annual = pd.DataFrame(
            row
            for _, enterprise in enterprises.iterrows()
            for row in simulate_enterprise(enterprise, variant, "cost_based_regime", "base")
        )
        row = build_portfolio_summary(annual, variant).iloc[0].to_dict()
        row["sensitivity_axis"] = "capex_rate"
        row["sensitivity_value"] = rate
        rows.append(row)
    for cap in [assumptions.annual_deduction_cap_pkr_m * 0.5, assumptions.annual_deduction_cap_pkr_m, assumptions.annual_deduction_cap_pkr_m * 1.5]:
        variant = replace(assumptions, annual_deduction_cap_pkr_m=cap)
        annual = pd.DataFrame(
            row
            for _, enterprise in enterprises.iterrows()
            for row in simulate_enterprise(enterprise, variant, "cost_based_regime", "base")
        )
        row = build_portfolio_summary(annual, variant).iloc[0].to_dict()
        row["sensitivity_axis"] = "annual_cap"
        row["sensitivity_value"] = cap
        rows.append(row)
    return pd.DataFrame(rows)


def build_parameter_ranges(enterprises: pd.DataFrame, assumptions: CalibrationAssumptions) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    envelope = _status_quo_proxy_envelope(enterprises, assumptions)
    for case in ADDITIONALITY_CASES:
        capex = solve_revenue_neutral_parameter(enterprises, assumptions, "capex_deduction_rate", 0.0, 2.0, envelope, case)
        cap = solve_revenue_neutral_parameter(enterprises, assumptions, "annual_deduction_cap_pkr_m", 0.0, 1000.0, envelope, case)
        rows.append(
            {
                "additionality_case": case,
                "capex_rate_status": capex["status"],
                "max_revenue_neutral_capex_rate": capex["value"],
                "annual_cap_status": cap["status"],
                "max_revenue_neutral_annual_cap_pkr_m": cap["value"],
                "rd_total_deduction_rate": assumptions.rd_super_deduction_total_rate,
                "rd_incremental_deduction_rate": max(0.0, assumptions.rd_super_deduction_total_rate - 1.0),
                "training_total_deduction_rate": assumptions.training_super_deduction_total_rate,
                "training_incremental_deduction_rate": max(0.0, assumptions.training_super_deduction_total_rate - 1.0),
                "qualifying_monetary_threshold_pkr_m": 0.0,
                "carry_forward_years": assumptions.carry_forward_years,
                "duration_sunset": "Temporary only; no SEZ-specific incentive after 30 June 2035.",
                "fiscal_envelope_pkr_m": round(envelope, 4),
                "envelope_type": "synthetic_proxy_status_quo",
                "model_version": MODEL_VERSION,
            }
        )
    return pd.DataFrame(rows)


def solve_revenue_neutral_parameter(
    enterprises: pd.DataFrame,
    assumptions: CalibrationAssumptions,
    parameter: str,
    lower: float,
    upper: float,
    envelope: float,
    additionality_case: str = "base",
    tolerance: float = 1e-3,
    max_iter: int = 40,
) -> dict[str, Any]:
    def cost_at(value: float) -> float:
        variant = replace(assumptions, **{parameter: value})
        annual = pd.DataFrame(
            row
            for _, enterprise in enterprises.iterrows()
            for row in simulate_enterprise(enterprise, variant, "cost_based_regime", additionality_case)
        )
        summary = build_portfolio_summary(annual, variant)
        row = summary[summary["scenario_id"] == "cost_based_regime"].iloc[0]
        return float(row["npv_gross_fiscal_cost_pkr_m"])

    low_cost = cost_at(lower)
    high_cost = cost_at(upper)
    if low_cost > envelope + tolerance:
        return {"status": "no_feasible_solution", "value": None, "cost_at_value": low_cost}
    if high_cost <= envelope + tolerance:
        return {"status": "entire_search_range_within_envelope", "value": upper, "cost_at_value": high_cost}
    lo, hi = lower, upper
    best = lower
    best_cost = low_cost
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        mid_cost = cost_at(mid)
        if mid_cost <= envelope + tolerance:
            best, best_cost = mid, mid_cost
            lo = mid
        else:
            hi = mid
    status = "feasible_interior_solution"
    if abs(best - lower) < tolerance or abs(best - upper) < tolerance:
        status = "feasible_only_at_boundary"
    return {"status": status, "value": round(best, 6), "cost_at_value": round(best_cost, 4)}


def build_reconciliation(enterprises: pd.DataFrame, zones: pd.DataFrame, assumptions: CalibrationAssumptions) -> pd.DataFrame:
    numeric_pairs = [
        ("investment_actual_pkr_m", "investment_actual_usd_m"),
        ("eligible_capex_pkr_m", "capex_eligible_usd_m"),
        ("eligible_rd_pkr_m", "rd_spend_usd_m"),
        ("eligible_training_pkr_m", "training_spend_usd_m"),
        ("cit_foregone_pkr_m_2026", "cit_foregone_pkr_m_2026"),
        ("customs_exemption_pkr_m_cumulative", "customs_exemption_pkr_m_cumulative"),
        ("tax_paid_pkr_m_2026", "tax_paid_pkr_m_2026"),
    ]
    rows = []
    for zone_id, group in enterprises.groupby("zone_id"):
        zone = zones[zones["zone_id"].astype(str) == str(zone_id)]
        zone_row = zone.iloc[0] if not zone.empty else pd.Series(dtype=object)
        for enterprise_field, zone_field in numeric_pairs:
            enterprise_sum = group[enterprise_field].sum() if enterprise_field in group.columns else 0.0
            zone_value = to_float(zone_row.get(zone_field)) if zone_field in zone_row.index else None
            if zone_field.endswith("_usd_m") and zone_value is not None:
                zone_value *= assumptions.fx_pkr_per_usd
            difference = None if zone_value is None else zone_value - enterprise_sum
            mismatch = bool(zone_value is not None and abs(difference or 0.0) > max(1.0, abs(zone_value) * 0.05))
            rows.append(
                {
                    "zone_id": zone_id,
                    "zone_name": group["zone_name"].iloc[0],
                    "field": enterprise_field,
                    "enterprise_sum_pkr_m": round(enterprise_sum, 4),
                    "zone_control_pkr_m": round(zone_value, 4) if zone_value is not None else pd.NA,
                    "difference_pkr_m": round(difference, 4) if difference is not None else pd.NA,
                    "mismatch_flag": mismatch,
                    "use_in_model": "enterprise_sum_only",
                    "note": "Zone value is a reconciliation/control total only and is not added to enterprise evidence.",
                }
            )
    return pd.DataFrame(rows)


def build_scenario_definitions(assumptions: CalibrationAssumptions) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"scenario_id": key, "scenario": value, "role": _scenario_role(key), "d5_envelope_test": key in {"cost_based_regime", "combined_transition_pilot"}, "model_version": MODEL_VERSION}
            for key, value in SCENARIOS.items()
        ]
    )


def build_d7_handoff(parameter_ranges: pd.DataFrame, verification: pd.DataFrame, assumptions: CalibrationAssumptions) -> pd.DataFrame:
    burden = verification.groupby("instrument", as_index=False)["burden_score"].mean()
    burden["administrative_feasibility_burden"] = burden["burden_score"].apply(_burden_label)
    rows = []
    for instrument in ["CAPEX", "R&D", "Training"]:
        reqs = verification[verification["instrument"].eq(instrument)]["requirement"].tolist()
        b = burden[burden["instrument"].eq(instrument)]
        rows.append(
            {
                "handoff_item": instrument,
                "parameter_range_to_test": _instrument_parameter_text(instrument, parameter_ranges),
                "cohort_eligibility_policy": assumptions.cohort_eligibility_policy,
                "claim_verification_evidence": "; ".join(reqs),
                "quarterly_kpi_fields": "claims filed; verified expenditure; uptake; processing time; disallowance reason; enterprise status",
                "semi_annual_evaluation_fields": "fiscal impact; additionality evidence; administrative feasibility; investor response; compliance findings",
                "launch_dependencies": "C2 legal authority; D4 legal review; D5/FBR fiscal verification; D6 calibration; Task Force/Finance decision",
                "pilot_timeline": "Design by 30 Oct 2026; launch June 2027; monitoring Sep 2027-Jun 2029; evaluation Jul-Aug 2029.",
                "pilot_selection_status": "No pilot zone selected by this model.",
                "administrative_feasibility_burden": b["administrative_feasibility_burden"].iloc[0] if not b.empty else "Not assessed",
                "model_version": MODEL_VERSION,
            }
        )
    return pd.DataFrame(rows)


def _instrument_parameter_text(instrument: str, parameter_ranges: pd.DataFrame) -> str:
    if parameter_ranges.empty:
        return "Not calculated"
    if instrument == "CAPEX":
        return "CAPEX expensing/rate range by additionality case: " + "; ".join(
            f"{row.additionality_case}: {row.max_revenue_neutral_capex_rate}" for row in parameter_ranges.itertuples()
        )
    if instrument == "R&D":
        return "R&D total rate 150%; incremental SEZ-specific rate 50%; subject to D5/D6 validation."
    return "Training total rate 150%; incremental SEZ-specific rate 50%; subject to D5/D6 validation."


def _blocked_frames(
    status: str,
    assumptions_frame: pd.DataFrame,
    scenario_definitions: pd.DataFrame,
    verification: pd.DataFrame,
    enterprises: pd.DataFrame | None = None,
    readiness: pd.DataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    status_df = pd.DataFrame([{"calibration_status": status, "blocked_reason": "Enterprise-level financial evidence is required before D6 calculations can run.", "model_version": MODEL_VERSION}])
    empty = pd.DataFrame()
    return {
        "calibration_enterprise_inputs": enterprises if enterprises is not None else empty,
        "calibration_assumptions": assumptions_frame,
        "calibration_scenario_definitions": scenario_definitions,
        "calibration_annual_enterprise": empty,
        "calibration_zone_aggregation": empty,
        "calibration_portfolio_summary": status_df,
        "calibration_sensitivity": empty,
        "calibration_parameter_ranges": empty,
        "calibration_verification_rules": verification,
        "calibration_d7_handoff": empty,
        "calibration_reconciliation": empty,
        "calibration_model_readiness": readiness if readiness is not None else status_df,
        "calibration_excluded_records": empty,
    }


def _load_assumptions_frame(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame([{"assumption_key": field, "value": getattr(CalibrationAssumptions(), field), "unit": "", "provenance": "code default", "editable": True, "description": ""} for field in CalibrationAssumptions.__dataclass_fields__])


def _assumptions_from_frame(frame: pd.DataFrame) -> CalibrationAssumptions:
    values: dict[str, Any] = {}
    fields = CalibrationAssumptions.__dataclass_fields__
    for _, row in frame.iterrows():
        key = str(row.get("assumption_key", "")).strip()
        if key not in fields:
            continue
        raw = row.get("value")
        if clean_text(raw) == "":
            values[key] = None
        elif fields[key].type in {int, "int"} or key.endswith("_year") or key.endswith("_years"):
            values[key] = int(float(raw))
        elif key == "cohort_eligibility_policy":
            values[key] = clean_text(raw)
        else:
            values[key] = float(raw)
    return CalibrationAssumptions(**values)


def _load_weights(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame(columns=["enterprise_id", "zone_id", "aggregation_weight", "cohort_scope", "maturity_category", "pilot_cohort_flag"])


def _load_verification_requirements(path: Path) -> pd.DataFrame:
    if path.exists():
        df = pd.read_csv(path)
    else:
        df = pd.DataFrame(columns=["instrument", "requirement", "owner", "burden_score", "source"])
    if "burden_score" in df.columns:
        df["burden_score"] = pd.to_numeric(df["burden_score"], errors="coerce")
        df["burden_label"] = df["burden_score"].apply(_burden_label)
    return df


def _assumptions_with_ui_overrides(
    assumptions: CalibrationAssumptions,
    scenario: dict[str, Any],
) -> CalibrationAssumptions:
    updates: dict[str, Any] = {}
    numeric_keys = {
        "d6_capex_deduction_rate": "capex_deduction_rate",
        "d6_annual_deduction_cap_pkr_m": "annual_deduction_cap_pkr_m",
        "d6_utilization_rate": "utilization_rate",
        "d6_discount_rate": "discount_rate",
    }
    for source_key, target_key in numeric_keys.items():
        if source_key not in scenario:
            continue
        parsed = to_float(scenario.get(source_key))
        if parsed is not None:
            updates[target_key] = parsed

    package = clean_text(scenario.get("d6_instrument_package")).lower()
    if package == "capex_only":
        updates["rd_super_deduction_total_rate"] = 1.0
        updates["training_super_deduction_total_rate"] = 1.0
    elif package == "rd_training":
        updates["capex_deduction_rate"] = 0.0

    return replace(assumptions, **updates) if updates else assumptions


def _assumptions_frame_with_overrides(
    frame: pd.DataFrame,
    assumptions: CalibrationAssumptions,
    scenario: dict[str, Any],
) -> pd.DataFrame:
    out = frame.copy()
    keys = CalibrationAssumptions.__dataclass_fields__
    if out.empty:
        out = _load_assumptions_frame(Path("__missing__"))
    for key in keys:
        if key not in out.get("assumption_key", pd.Series(dtype=str)).astype(str).tolist():
            out = pd.concat(
                [
                    out,
                    pd.DataFrame(
                        [
                            {
                                "assumption_key": key,
                                "value": getattr(assumptions, key),
                                "unit": "",
                                "provenance": "code default",
                                "editable": True,
                                "description": "",
                            }
                        ]
                    ),
                ],
                ignore_index=True,
            )
        out.loc[out["assumption_key"].astype(str).eq(key), "value"] = clean_text(getattr(assumptions, key))
    if scenario:
        out["active_ui_override"] = out["assumption_key"].astype(str).isin(
            {
                "capex_deduction_rate",
                "annual_deduction_cap_pkr_m",
                "utilization_rate",
                "discount_rate",
                "rd_super_deduction_total_rate",
                "training_super_deduction_total_rate",
            }
        )
    return out


def _blocked_reason(row: pd.Series) -> str:
    reasons = []
    if row.get("epz_excluded"):
        reasons.append("EPZ cohort excluded from default SEZ calibration slice.")
    if not row.get("legal_ready"):
        reasons.append("D4 legal readiness not cleared.")
    if not row.get("fiscal_ready"):
        reasons.append("D5/FBR fiscal verification not cleared.")
    if not row.get("compliance_ready"):
        reasons.append("Developer/enterprise compliance not cleared.")
    if pd.isna(row.get("baseline_assessed_income_pkr_m")):
        reasons.append("Enterprise assessed-income basis missing.")
    return " ".join(reasons) if reasons else "Gate-cleared for synthetic D6 modelling."


def _scenario_role(scenario_id: str) -> str:
    return {
        "status_quo_to_2035": "2026-2035 baseline fiscal-cost envelope scenario.",
        "accelerated_removal": "Transition scenario for non-compliant zones/enterprises.",
        "cost_based_regime": "Candidate CAPEX/R&D/training cost-based scenario tested against the envelope.",
        "combined_transition_pilot": "Combined accelerated-removal and pilot-uptake scenario.",
        "no_sez_specific_incentive": "Counterfactual tax benchmark, not a transition scenario substitute.",
    }[scenario_id]


def _fiscal_envelope(annual: pd.DataFrame, assumptions: CalibrationAssumptions) -> float:
    if assumptions.d5_fiscal_envelope_pkr_m is not None:
        return assumptions.d5_fiscal_envelope_pkr_m
    status = annual[(annual["scenario_id"] == "status_quo_to_2035") & (annual["additionality_case"] == "base")]
    if status.empty:
        return 0.0
    return float((status["gross_fiscal_cost_pkr_m"] * status["aggregation_weight"] * status["discount_factor"]).sum())


def _status_quo_proxy_envelope(enterprises: pd.DataFrame, assumptions: CalibrationAssumptions) -> float:
    annual = pd.DataFrame(
        row
        for _, enterprise in enterprises.iterrows()
        for row in simulate_enterprise(enterprise, assumptions, "status_quo_to_2035", "base")
    )
    return _fiscal_envelope(annual, assumptions)


def _cit_phase_in_factor(year: int, assumptions: CalibrationAssumptions) -> float:
    if year > assumptions.projection_end_year:
        return 1.0
    years = assumptions.projection_end_year - assumptions.projection_start_year + 1
    return min(1.0, max(0.1, (year - assumptions.projection_start_year + 1) / years))


def _annualized_customs(cumulative: float, year: int, assumptions: CalibrationAssumptions) -> float:
    end_year = assumptions.projection_start_year + assumptions.status_quo_customs_annualization_years - 1
    if assumptions.projection_start_year <= year <= end_year:
        return cumulative / max(assumptions.status_quo_customs_annualization_years, 1)
    return 0.0


def _expire_carryforward(entries: list[dict[str, float | int]], year: int) -> tuple[list[dict[str, float | int]], float]:
    active = []
    expired = 0.0
    for entry in entries:
        if int(entry["expiry_year"]) < year:
            expired += float(entry["amount"])
        else:
            active.append(entry)
    return active, expired


def _use_carryforward_fifo(entries: list[dict[str, float | int]], taxable_income: float, year: int) -> tuple[float, float, list[dict[str, float | int]]]:
    remaining_need = max(0.0, taxable_income)
    used = 0.0
    carryforward_used = 0.0
    updated = []
    for entry in sorted(entries, key=lambda e: (int(e["expiry_year"]), int(e["origin_year"]))):
        amount = float(entry["amount"])
        use = min(amount, remaining_need)
        amount -= use
        remaining_need -= use
        used += use
        if int(entry["origin_year"]) < year:
            carryforward_used += use
        if amount > 1e-9:
            updated.append({**entry, "amount": amount})
    return used, carryforward_used, updated


def _burden_label(score: float | int | None) -> str:
    value = 0.0 if pd.isna(score) else float(score)
    if value <= 1.5:
        return "Low"
    if value <= 2.4:
        return "Medium"
    return "High"


def _num(row: pd.Series | dict[str, Any], key: str, default: float = 0.0) -> float:
    value = row.get(key, default)
    parsed = to_float(value)
    return default if parsed is None else float(parsed)


def _to_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}
