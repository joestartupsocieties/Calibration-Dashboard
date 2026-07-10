from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pandas as pd

from .utils import clean_text, safe_divide, to_float


MODEL_VERSION = "d6-calibration-mvp-v0.2.1"
YEARS = list(range(2026, 2036))
SCENARIOS = {
    "no_sez_specific_incentive": "No SEZ-specific incentive reference",
    "status_quo_to_2035": "Status quo to 2035",
    "accelerated_removal": "Accelerated removal for non-compliant enterprises",
    "cost_based_regime": "Temporary cost-based deduction regime",
    "combined_transition_pilot": "Combined transition plus pilot uptake",
}
ADDITIONALITY_CASES = ("low", "base", "high")
INSTRUMENT_PACKAGES = {
    "full": "CAPEX / R&D / training package",
    "capex_only": "CAPEX-only package",
    "rd_training": "R&D / training package",
}


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
    instrument_package: str = "full"
    capex_deduction_rate: float = 0.75
    rd_super_deduction_total_rate: float = 1.5
    training_super_deduction_total_rate: float = 1.5
    utilization_rate: float = 0.80
    annual_deduction_cap_pkr_m: float = 18_000.0
    qualifying_expenditure_threshold_pkr_m: float = 3_000.0
    carry_forward_years: int = 3
    additionality_low: float = 0.08
    additionality_base: float = 0.22
    additionality_high: float = 0.38
    status_quo_additionality_factor: float = 0.35
    taxable_return_on_incremental_expenditure: float = 0.18
    additionality_income_lag_years: int = 1
    admin_cost_per_enterprise_pkr_m: float = 0.0
    admin_review_hours_per_claim: float = 24.0
    admin_audit_hours_per_claim: float = 72.0
    audit_sample_rate: float = 0.25
    admin_cost_per_review_hour_pkr_m: float = 0.018
    fixed_admin_cost_per_claim_pkr_m: float = 0.35
    annual_fte_hours: float = 1_760.0
    status_quo_customs_annualization_years: int = 5
    d5_fiscal_envelope_pkr_m: float | None = 30_000.0
    fiscal_envelope_definition: str = "illustrative_D5_fiscal_ceiling_for_synthetic_cost_based_pilot"
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
    evidence_ready = enterprises[enterprises["evidence_model_ready"].astype(bool)].copy()

    if evidence_ready.empty:
        return _blocked_frames("no_synthetic_model_ready_enterprises", assumptions_frame, scenario_definitions, verification, enterprises, readiness)

    annual = build_annual_results(evidence_ready, assumptions)
    zone_aggregation = build_zone_aggregation(annual)
    portfolio_summary = build_portfolio_summary(annual, assumptions)
    sensitivity = build_sensitivity(evidence_ready, assumptions)
    parameter_ranges = build_parameter_ranges(evidence_ready, assumptions)
    reconciliation = build_reconciliation(enterprises, zones, assumptions)
    d7_handoff = build_d7_handoff(parameter_ranges, verification, assumptions)
    excluded = enterprises[~enterprises["evidence_model_ready"].astype(bool)].copy()

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
    numeric_fields = {
        "employment_actual",
        "tax_paid_pkr_m_2026",
        "cit_foregone_pkr_m_2026",
        "customs_exemption_pkr_m_cumulative",
        "public_infrastructure_cost_pkr_m",
        "land_concession_pkr_m",
    }
    for col in df.columns:
        if col.endswith(("_usd_m", "_pkr_m", "_pkr_m_2026", "_pkr_m_cumulative")) or col in numeric_fields:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.merge(weights, on=["enterprise_id", "zone_id"], how="left")
    df["aggregation_weight"] = pd.to_numeric(df.get("aggregation_weight"), errors="coerce").fillna(1.0)
    df["cohort_scope"] = df.get("cohort_scope", "SEZ").fillna("SEZ").astype(str)
    df["pilot_cohort_flag"] = df.get("pilot_cohort_flag", False).apply(_to_bool)
    df["maturity_category"] = df.get("maturity_category", "").fillna("").astype(str)
    df["fx_pkr_per_usd"] = assumptions.fx_pkr_per_usd

    usd_fields = [
        "investment_actual_usd_m",
        "exports_usd_m_2026",
        "domestic_sales_usd_m_2026",
        "capex_eligible_usd_m",
        "rd_spend_usd_m",
        "training_spend_usd_m",
    ]
    for field in usd_fields:
        if field in df.columns:
            df[f"{field.replace('_usd_m', '')}_pkr_m"] = pd.to_numeric(df[field], errors="coerce") * assumptions.fx_pkr_per_usd

    for field in ["cit_foregone_pkr_m_2026", "tax_paid_pkr_m_2026", "customs_exemption_pkr_m_cumulative"]:
        if field not in df.columns:
            df[field] = pd.NA

    df["ordinary_benchmark_tax_pkr_m_2026"] = df[["cit_foregone_pkr_m_2026", "tax_paid_pkr_m_2026"]].sum(axis=1, min_count=1)
    df["baseline_assessed_income_pkr_m"] = df["ordinary_benchmark_tax_pkr_m_2026"] / assumptions.statutory_cit_rate
    df["eligible_capex_pkr_m"] = df.get("capex_eligible_pkr_m", pd.Series(0.0, index=df.index)).fillna(0.0)
    df["eligible_rd_pkr_m"] = df.get("rd_spend_pkr_m", pd.Series(0.0, index=df.index)).fillna(0.0)
    df["eligible_training_pkr_m"] = df.get("training_spend_pkr_m", pd.Series(0.0, index=df.index)).fillna(0.0)
    df["public_infrastructure_cost_pkr_m"] = pd.to_numeric(
        df.get("public_infrastructure_cost_pkr_m", pd.Series(0.0, index=df.index)),
        errors="coerce",
    ).fillna(0.0)
    df["land_concession_pkr_m"] = pd.to_numeric(
        df.get("land_concession_pkr_m", pd.Series(0.0, index=df.index)),
        errors="coerce",
    ).fillna(0.0)

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
    df["financial_evidence_complete"] = (
        df["baseline_assessed_income_pkr_m"].notna()
        & df["tax_paid_pkr_m_2026"].notna()
        & df["cit_foregone_pkr_m_2026"].notna()
        & df["customs_exemption_pkr_m_cumulative"].notna()
    )
    df["record_quality_status"] = df["data_confidence_band"].fillna("not assessed")
    df["substantive_evidence_status"] = "synthetic/unvalidated"
    df["epz_excluded"] = df["cohort_scope"].str.upper().eq("EPZ")
    df["evidence_model_ready"] = df["financial_evidence_complete"] & ~df["epz_excluded"]
    df["model_ready"] = df["evidence_model_ready"]
    df["support_eligibility_status"] = df.apply(_support_eligibility_status, axis=1)
    df["transition_treatment_status"] = df.apply(_transition_treatment_status, axis=1)
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
        "financial_evidence_complete",
        "evidence_model_ready",
        "model_ready",
        "support_eligibility_status",
        "transition_treatment_status",
        "record_quality_status",
        "substantive_evidence_status",
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
    if scenario_id == "combined_transition_pilot":
        return _simulate_combined_enterprise(enterprise, assumptions, additionality_case)

    carryforward: list[dict[str, float | int]] = []
    rows: list[dict[str, Any]] = []
    base_income = _num(enterprise, "baseline_assessed_income_pkr_m")
    capex_base = _num(enterprise, "eligible_capex_pkr_m")
    rd_base = _num(enterprise, "eligible_rd_pkr_m")
    training_base = _num(enterprise, "eligible_training_pkr_m")
    customs_cumulative = _num(enterprise, "customs_exemption_pkr_m_cumulative")
    indirect_base = _num(enterprise, "public_infrastructure_cost_pkr_m") + _num(enterprise, "land_concession_pkr_m")
    weight = _num(enterprise, "aggregation_weight", 1.0)
    support_can_claim = _support_can_claim(enterprise)
    non_compliant = _is_non_compliant(enterprise)

    for year in YEARS:
        n = year - assumptions.projection_start_year
        discount_factor = 1 / ((1 + assumptions.discount_rate) ** n)
        reference_income = base_income * ((1 + assumptions.assessed_income_growth) ** n)
        capex = capex_base * ((1 + assumptions.eligible_expenditure_growth) ** n)
        rd = rd_base * ((1 + assumptions.eligible_expenditure_growth) ** n)
        training = training_base * ((1 + assumptions.eligible_expenditure_growth) ** n)
        lag_n = n - assumptions.additionality_income_lag_years
        prior_growth = 0.0 if lag_n < 0 else ((1 + assumptions.eligible_expenditure_growth) ** lag_n)
        prior_capex = capex_base * prior_growth
        prior_rd = rd_base * prior_growth
        prior_training = training_base * prior_growth
        incentive_signal = _incentive_signal(
            prior_capex,
            prior_rd,
            prior_training,
            scenario_id,
            assumptions,
            support_can_claim,
        )
        scenario_additionality = _scenario_additionality_share(enterprise, assumptions, scenario_id, additionality_case)
        responsive_expenditure = incentive_signal["responsive_expenditure_pkr_m"]
        incremental_income = responsive_expenditure * scenario_additionality * assumptions.taxable_return_on_incremental_expenditure
        assessed_income = reference_income + incremental_income
        reference_tax_liability = max(0.0, reference_income * assumptions.statutory_cit_rate)
        benchmark_tax_liability = max(0.0, assessed_income * assumptions.statutory_cit_rate)

        deduction_data = _empty_deduction_data()
        tax_due = benchmark_tax_liability
        customs_expenditure = 0.0
        admin_cost = 0.0
        review_hours = 0.0
        fte_requirement = 0.0
        state = "Ordinary CIT / no SEZ-specific incentive reference"

        if scenario_id == "status_quo_to_2035":
            state = "Protected status-quo treatment through the 2035 hard cap"
            if year <= assumptions.holiday_expiry_year:
                tax_due = benchmark_tax_liability * (1 - assumptions.current_holiday_exemption_share)
            customs_expenditure = _annualized_customs(customs_cumulative, year, assumptions)
        elif scenario_id == "accelerated_removal":
            if non_compliant:
                state = "Accelerated removal: non-compliant enterprise moved to ordinary CIT"
                tax_due = benchmark_tax_liability
                customs_expenditure = 0.0
            else:
                state = "No acceleration trigger: status-quo treatment retained"
                if year <= assumptions.holiday_expiry_year:
                    tax_due = benchmark_tax_liability * (1 - assumptions.current_holiday_exemption_share)
                customs_expenditure = _annualized_customs(customs_cumulative, year, assumptions)
        elif scenario_id == "cost_based_regime":
            state = "Ordinary CIT plus temporary cost-based deductions"
            if support_can_claim:
                tax_due, deduction_data, carryforward = _apply_cost_based_deductions(
                    assessed_income, capex, rd, training, carryforward, assumptions, year
                )
                admin_cost, review_hours, fte_requirement = _administrative_cost(deduction_data, assumptions, enterprise)
            else:
                state = "Ordinary CIT: support-review gates not cleared"

        tax_due = max(0.0, tax_due)
        tax_expenditure = max(0.0, benchmark_tax_liability - tax_due)
        other_cash_cost = indirect_base / len(YEARS)
        gross_fiscal_cost = tax_expenditure + customs_expenditure + admin_cost + other_cash_cost
        cash_net_revenue = tax_due - admin_cost - other_cash_cost
        reference_cash_net_revenue = reference_tax_liability
        fiscal_impact_vs_reference = cash_net_revenue - reference_cash_net_revenue
        after_tax_income = assessed_income - tax_due
        cost_per_incremental_income = safe_divide(gross_fiscal_cost, incremental_income)

        rows.append(
            {
                "enterprise_id": enterprise.get("enterprise_id"),
                "zone_id": enterprise.get("zone_id"),
                "zone_name": enterprise.get("zone_name"),
                "sector": enterprise.get("sector"),
                "cohort_scope": enterprise.get("cohort_scope"),
                "maturity_category": enterprise.get("maturity_category"),
                "aggregation_weight": weight,
                "evidence_model_ready": bool(enterprise.get("evidence_model_ready", enterprise.get("model_ready", False))),
                "support_eligibility_status": enterprise.get("support_eligibility_status", "not assessed"),
                "transition_treatment_status": enterprise.get("transition_treatment_status", "not assessed"),
                "scenario_id": scenario_id,
                "scenario": SCENARIOS[scenario_id],
                "enterprise_tax_state": state,
                "additionality_case": additionality_case,
                "fiscal_year": year,
                "reference_assessed_income_pkr_m": round(reference_income, 4),
                "assessed_income_before_relief_pkr_m": round(assessed_income, 4),
                "additionality_share": round(scenario_additionality, 6),
                "potential_incentive_deduction_pkr_m": round(incentive_signal["potential_incentive_deduction_pkr_m"], 4),
                "incentive_intensity_factor": round(incentive_signal["incentive_intensity_factor"], 6),
                "responsive_expenditure_pkr_m": round(responsive_expenditure, 4),
                "incentive_availability_status": incentive_signal["incentive_availability_status"],
                "incremental_assessed_income_pkr_m": round(incremental_income, 4),
                "benchmark_tax_liability_pkr_m": round(benchmark_tax_liability, 4),
                "ordinary_reference_tax_pkr_m": round(reference_tax_liability, 4),
                "benchmark_tax_no_sez_pkr_m": round(benchmark_tax_liability, 4),
                "tax_due_pkr_m": round(tax_due, 4),
                "tax_collected_pkr_m": round(tax_due, 4),
                "effective_tax_rate": round(safe_divide(tax_due, assessed_income) or 0.0, 6),
                "eligible_capex_pkr_m": round(capex, 4),
                "eligible_rd_pkr_m": round(rd, 4),
                "eligible_training_pkr_m": round(training, 4),
                "total_qualifying_expenditure_pkr_m": round(capex + rd + training, 4),
                "qualifying_expenditure_threshold_pkr_m": round(assumptions.qualifying_expenditure_threshold_pkr_m, 4),
                **{
                    key: (value if isinstance(value, bool) else round(value, 4) if isinstance(value, (float, int)) else value)
                    for key, value in deduction_data.items()
                },
                "tax_expenditure_pkr_m": round(tax_expenditure, 4),
                "direct_cit_expenditure_pkr_m": round(tax_expenditure, 4),
                "customs_expenditure_pkr_m": round(customs_expenditure, 4),
                "incremental_admin_cost_pkr_m": round(admin_cost, 4),
                "admin_review_hours": round(review_hours, 4),
                "admin_fte_requirement": round(fte_requirement, 6),
                "other_government_cash_cost_pkr_m": round(other_cash_cost, 4),
                "indirect_cost_allocated_pkr_m": round(other_cash_cost, 4),
                "gross_fiscal_cost_pkr_m": round(gross_fiscal_cost, 4),
                "cash_net_revenue_pkr_m": round(cash_net_revenue, 4),
                "reference_cash_net_revenue_pkr_m": round(reference_cash_net_revenue, 4),
                "fiscal_impact_vs_reference_pkr_m": round(fiscal_impact_vs_reference, 4),
                "net_fiscal_position_pkr_m": round(cash_net_revenue, 4),
                "after_tax_income_pkr_m": round(after_tax_income, 4),
                "fiscal_cost_per_incremental_income": round(cost_per_incremental_income, 6) if cost_per_incremental_income is not None else pd.NA,
                "discount_factor": round(discount_factor, 8),
                "npv_gross_fiscal_cost_pkr_m": round(gross_fiscal_cost * discount_factor, 4),
                "npv_tax_expenditure_pkr_m": round(tax_expenditure * discount_factor, 4),
                "npv_cash_net_revenue_pkr_m": round(cash_net_revenue * discount_factor, 4),
                "npv_fiscal_impact_vs_reference_pkr_m": round(fiscal_impact_vs_reference * discount_factor, 4),
                "npv_incremental_assessed_income_pkr_m": round(incremental_income * discount_factor, 4),
                "weighted_gross_fiscal_cost_pkr_m": round(gross_fiscal_cost * weight, 4),
                "weighted_tax_collected_pkr_m": round(tax_due * weight, 4),
                "weighted_after_tax_income_pkr_m": round(after_tax_income * weight, 4),
                "model_version": MODEL_VERSION,
                "formula_reference": "docs/D6_MODEL_METHOD.md",
            }
        )
    return rows


def _simulate_combined_enterprise(
    enterprise: pd.Series | dict[str, Any],
    assumptions: CalibrationAssumptions,
    additionality_case: str,
) -> list[dict[str, Any]]:
    non_pilot_scenario = "accelerated_removal" if _is_non_compliant(enterprise) else "status_quo_to_2035"
    non_pilot = simulate_enterprise(enterprise, assumptions, non_pilot_scenario, additionality_case)
    if not (_to_bool(enterprise.get("pilot_cohort_flag")) and _support_can_claim(enterprise)):
        return [_combined_row(row, row, 0.0, non_pilot_scenario) for row in non_pilot]
    pilot = simulate_enterprise(enterprise, assumptions, "cost_based_regime", additionality_case)
    uptake = min(max(float(assumptions.pilot_uptake_share), 0.0), 1.0)
    return [_combined_row(base, pilot_row, uptake, non_pilot_scenario) for base, pilot_row in zip(non_pilot, pilot)]


def _combined_row(base: dict[str, Any], pilot: dict[str, Any], uptake: float, non_pilot_scenario: str) -> dict[str, Any]:
    out = dict(base)
    numeric_blend = {
        "reference_assessed_income_pkr_m",
        "assessed_income_before_relief_pkr_m",
        "additionality_share",
        "potential_incentive_deduction_pkr_m",
        "incentive_intensity_factor",
        "responsive_expenditure_pkr_m",
        "incremental_assessed_income_pkr_m",
        "benchmark_tax_liability_pkr_m",
        "ordinary_reference_tax_pkr_m",
        "benchmark_tax_no_sez_pkr_m",
        "tax_due_pkr_m",
        "tax_collected_pkr_m",
        "eligible_capex_pkr_m",
        "eligible_rd_pkr_m",
        "eligible_training_pkr_m",
        "total_qualifying_expenditure_pkr_m",
        "capex_incremental_deduction_pkr_m",
        "ordinary_capex_depreciation_offset_pkr_m",
        "rd_incremental_deduction_pkr_m",
        "training_incremental_deduction_pkr_m",
        "deduction_generated_before_utilization_pkr_m",
        "deduction_generated_pkr_m",
        "deduction_used_pkr_m",
        "carryforward_used_pkr_m",
        "deduction_expired_pkr_m",
        "closing_carryforward_pkr_m",
        "current_year_potential_incentive_deduction_pkr_m",
        "current_year_incentive_intensity_factor",
        "tax_expenditure_pkr_m",
        "direct_cit_expenditure_pkr_m",
        "customs_expenditure_pkr_m",
        "incremental_admin_cost_pkr_m",
        "admin_review_hours",
        "admin_fte_requirement",
        "other_government_cash_cost_pkr_m",
        "indirect_cost_allocated_pkr_m",
        "gross_fiscal_cost_pkr_m",
        "cash_net_revenue_pkr_m",
        "reference_cash_net_revenue_pkr_m",
        "fiscal_impact_vs_reference_pkr_m",
        "net_fiscal_position_pkr_m",
        "after_tax_income_pkr_m",
        "npv_gross_fiscal_cost_pkr_m",
        "npv_tax_expenditure_pkr_m",
        "npv_cash_net_revenue_pkr_m",
        "npv_fiscal_impact_vs_reference_pkr_m",
        "npv_incremental_assessed_income_pkr_m",
        "weighted_gross_fiscal_cost_pkr_m",
        "weighted_tax_collected_pkr_m",
        "weighted_after_tax_income_pkr_m",
    }
    for key in numeric_blend:
        out[key] = round(_num(base, key) * (1 - uptake) + _num(pilot, key) * uptake, 4)
    out["effective_tax_rate"] = round(safe_divide(out["tax_due_pkr_m"], out["assessed_income_before_relief_pkr_m"]) or 0.0, 6)
    out["fiscal_cost_per_incremental_income"] = (
        round(safe_divide(out["gross_fiscal_cost_pkr_m"], out["incremental_assessed_income_pkr_m"]) or 0.0, 6)
        if out["incremental_assessed_income_pkr_m"]
        else pd.NA
    )
    out["scenario_id"] = "combined_transition_pilot"
    out["scenario"] = SCENARIOS["combined_transition_pilot"]
    out["enterprise_tax_state"] = f"Blended pilot uptake {uptake:.0%}; non-pilot path: {non_pilot_scenario}"
    out["pilot_uptake_share"] = uptake
    out["non_pilot_scenario_id"] = non_pilot_scenario
    out["pilot_tax_state"] = pilot.get("enterprise_tax_state", "")
    out["threshold_met"] = bool(pilot.get("threshold_met", base.get("threshold_met", False))) if uptake else bool(base.get("threshold_met", False))
    out["incentive_availability_status"] = pilot.get("incentive_availability_status", base.get("incentive_availability_status", "")) if uptake else base.get("incentive_availability_status", "")
    out["binding_constraint"] = pilot.get("binding_constraint", base.get("binding_constraint", "not_applicable")) if uptake else base.get("binding_constraint", "not_applicable")
    return out


def _apply_cost_based_deductions(
    benchmark_income: float,
    capex: float,
    rd: float,
    training: float,
    carryforward: list[dict[str, float | int]],
    assumptions: CalibrationAssumptions,
    year: int,
) -> tuple[float, dict[str, Any], list[dict[str, float | int]]]:
    carryforward, expired = _expire_carryforward(carryforward, year)
    incentive = _cost_based_incentive_signal(capex, rd, training, assumptions)
    ordinary_offset = incentive["ordinary_capex_depreciation_offset_pkr_m"]
    threshold_met = bool(incentive["threshold_met"])
    capex_incremental = incentive["capex_incremental_deduction_pkr_m"]
    rd_incremental = incentive["rd_incremental_deduction_pkr_m"]
    training_incremental = incentive["training_incremental_deduction_pkr_m"]
    generated_before_utilization = incentive["deduction_generated_before_utilization_pkr_m"]
    generated_after_utilization = incentive["deduction_generated_after_utilization_pkr_m"]
    generated = incentive["potential_incentive_deduction_pkr_m"]
    current_entry = {"amount": generated, "expiry_year": year + assumptions.carry_forward_years, "origin_year": year}
    available_entries = carryforward + ([current_entry] if generated > 0 else [])
    used, carryforward_used, updated_entries = _use_carryforward_fifo(available_entries, benchmark_income, year)
    taxable_income_after_deduction = max(0.0, benchmark_income - used)
    tax_due = max(0.0, taxable_income_after_deduction * assumptions.statutory_cit_rate)
    closing = sum(float(entry["amount"]) for entry in updated_entries)
    binding = _deduction_binding_constraint(threshold_met, generated_before_utilization, generated_after_utilization, generated, used, closing, assumptions)
    return tax_due, {
        "capex_incremental_deduction_pkr_m": capex_incremental,
        "ordinary_capex_depreciation_offset_pkr_m": ordinary_offset,
        "rd_incremental_deduction_pkr_m": rd_incremental,
        "training_incremental_deduction_pkr_m": training_incremental,
        "deduction_generated_before_utilization_pkr_m": generated_before_utilization,
        "deduction_generated_after_utilization_pkr_m": generated_after_utilization,
        "deduction_generated_pkr_m": generated,
        "deduction_used_pkr_m": used,
        "carryforward_used_pkr_m": carryforward_used,
        "deduction_expired_pkr_m": expired,
        "closing_carryforward_pkr_m": closing,
        "current_year_potential_incentive_deduction_pkr_m": generated,
        "current_year_incentive_intensity_factor": incentive["incentive_intensity_factor"],
        "threshold_met": bool(threshold_met),
        "binding_constraint": binding,
    }, updated_entries


def build_zone_aggregation(annual: pd.DataFrame) -> pd.DataFrame:
    if annual.empty:
        return pd.DataFrame()
    df = annual.copy()
    for col in [
        "gross_fiscal_cost_pkr_m",
        "tax_collected_pkr_m",
        "cash_net_revenue_pkr_m",
        "fiscal_impact_vs_reference_pkr_m",
        "after_tax_income_pkr_m",
        "incremental_assessed_income_pkr_m",
        "npv_gross_fiscal_cost_pkr_m",
        "npv_cash_net_revenue_pkr_m",
        "npv_fiscal_impact_vs_reference_pkr_m",
    ]:
        if col in df.columns:
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
    envelope = _fiscal_envelope(df, assumptions)
    for keys, group in df.groupby(group_cols):
        scenario_id, scenario, additionality_case = keys
        weighted_cost_npv = _weighted_npv(group, "gross_fiscal_cost_pkr_m")
        weighted_tax_npv = _weighted_npv(group, "tax_collected_pkr_m")
        weighted_tax_expenditure_npv = _weighted_npv(group, "tax_expenditure_pkr_m")
        weighted_cash_net_npv = _weighted_npv(group, "cash_net_revenue_pkr_m")
        weighted_impact_npv = _weighted_npv(group, "fiscal_impact_vs_reference_pkr_m")
        weighted_after_tax_npv = _weighted_npv(group, "after_tax_income_pkr_m")
        weighted_incremental_income_npv = _weighted_npv(group, "incremental_assessed_income_pkr_m")
        weighted_admin_cost_npv = _weighted_npv(group, "incremental_admin_cost_pkr_m")
        if "admin_review_hours" in group:
            weighted_hours = group["admin_review_hours"] * group["aggregation_weight"]
            review_hours = float(weighted_hours.sum())
            annual_hours = (
                pd.DataFrame({"fiscal_year": group["fiscal_year"], "weighted_hours": weighted_hours})
                .groupby("fiscal_year")["weighted_hours"]
                .sum()
            )
            peak_annual_hours = float(annual_hours.max()) if not annual_hours.empty else 0.0
            average_annual_hours = float(annual_hours.mean()) if not annual_hours.empty else 0.0
        else:
            review_hours = 0.0
            peak_annual_hours = 0.0
            average_annual_hours = 0.0
        rows.append(
            {
                "scenario_id": scenario_id,
                "scenario": scenario,
                "additionality_case": additionality_case,
                "npv_gross_fiscal_cost_pkr_m": round(weighted_cost_npv, 4),
                "npv_tax_collected_pkr_m": round(weighted_tax_npv, 4),
                "npv_tax_expenditure_pkr_m": round(weighted_tax_expenditure_npv, 4),
                "npv_cash_net_revenue_pkr_m": round(weighted_cash_net_npv, 4),
                "npv_fiscal_impact_vs_reference_pkr_m": round(weighted_impact_npv, 4),
                "npv_enterprise_after_tax_income_pkr_m": round(weighted_after_tax_npv, 4),
                "npv_incremental_assessed_income_pkr_m": round(weighted_incremental_income_npv, 4),
                "npv_admin_cost_pkr_m": round(weighted_admin_cost_npv, 4),
                "review_workload_hours": round(review_hours, 4),
                "peak_annual_review_workload_hours": round(peak_annual_hours, 4),
                "average_annual_review_workload_hours": round(average_annual_hours, 4),
                "indicative_fte_requirement": round(peak_annual_hours / assumptions.annual_fte_hours, 6),
                "average_annual_fte_requirement": round(average_annual_hours / assumptions.annual_fte_hours, 6),
                "fiscal_cost_per_incremental_income": (
                    round(weighted_cost_npv / weighted_incremental_income_npv, 6) if weighted_incremental_income_npv else "Not estimable"
                ),
                "fiscal_envelope_type": _fiscal_envelope_type(assumptions),
                "fiscal_envelope_definition": assumptions.fiscal_envelope_definition,
                "fiscal_envelope_pkr_m": round(envelope, 4),
                "envelope_margin_pkr_m": round(envelope - weighted_cost_npv, 4),
                "within_envelope": bool(weighted_cost_npv <= envelope),
                "model_version": MODEL_VERSION,
            }
        )
    return pd.DataFrame(rows)


def build_sensitivity(enterprises: pd.DataFrame, assumptions: CalibrationAssumptions) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for case in ADDITIONALITY_CASES:
        rows.append(_sensitivity_row(enterprises, assumptions, "additionality", case, additionality_case=case))
    for rate in [0.0, 0.5, assumptions.capex_deduction_rate, 1.0, 1.25]:
        rows.append(_sensitivity_row(enterprises, replace(assumptions, capex_deduction_rate=rate), "capex_rate", rate))
    for cap in [1_500.0, assumptions.annual_deduction_cap_pkr_m, 10_000.0]:
        rows.append(_sensitivity_row(enterprises, replace(assumptions, annual_deduction_cap_pkr_m=cap), "annual_cap", cap))
    for threshold in [0.0, assumptions.qualifying_expenditure_threshold_pkr_m, 6_000.0]:
        rows.append(_sensitivity_row(enterprises, replace(assumptions, qualifying_expenditure_threshold_pkr_m=threshold), "qualifying_threshold", threshold))
    for package in ["capex_only", "rd_training", "full"]:
        rows.append(_sensitivity_row(enterprises, replace(assumptions, instrument_package=package), "instrument_package", package))
    for utilization in [0.5, assumptions.utilization_rate, 1.0]:
        rows.append(_sensitivity_row(enterprises, replace(assumptions, utilization_rate=utilization), "utilization", utilization))
    return pd.DataFrame(rows)


def _sensitivity_row(
    enterprises: pd.DataFrame,
    assumptions: CalibrationAssumptions,
    axis: str,
    value: object,
    *,
    scenario_id: str = "cost_based_regime",
    additionality_case: str = "base",
) -> dict[str, Any]:
    annual = pd.DataFrame(
        row
        for _, enterprise in enterprises.iterrows()
        for row in simulate_enterprise(enterprise, assumptions, scenario_id, additionality_case)
    )
    row = build_portfolio_summary(annual, assumptions).iloc[0].to_dict()
    row["sensitivity_axis"] = axis
    row["sensitivity_value"] = value
    row["fiscal_envelope_pkr_m"] = _fiscal_envelope(annual, assumptions)
    row["fiscal_envelope_definition"] = assumptions.fiscal_envelope_definition
    return row


def build_parameter_ranges(enterprises: pd.DataFrame, assumptions: CalibrationAssumptions) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    envelope = _fiscal_envelope(pd.DataFrame(), assumptions)
    packages = ["capex_only", "rd_training", "full"]
    rates = [0.0, 0.75, 1.25]
    caps = [3_000.0, 18_000.0, 25_000.0]
    thresholds = [0.0, 3_000.0]
    utilizations = [0.8]
    uptakes = [0.0, 0.6, 1.0]
    for case in ADDITIONALITY_CASES:
        for package in packages:
            for rate in rates:
                for cap in caps:
                    for threshold in thresholds:
                        for utilization in utilizations:
                            for uptake in uptakes:
                                variant = replace(
                                    assumptions,
                                    instrument_package=package,
                                    capex_deduction_rate=rate,
                                    annual_deduction_cap_pkr_m=cap,
                                    qualifying_expenditure_threshold_pkr_m=threshold,
                                    utilization_rate=utilization,
                                    pilot_uptake_share=uptake,
                                )
                                support_pool = enterprises[enterprises.apply(_support_can_claim, axis=1)].copy()
                                model_pool = support_pool if not support_pool.empty else enterprises
                                annual = pd.DataFrame(
                                    row
                                    for _, enterprise in model_pool.iterrows()
                                    for row in simulate_enterprise(enterprise, variant, "cost_based_regime", case)
                                )
                                summary = build_portfolio_summary(annual, variant)
                                portfolio = summary[summary["scenario_id"].eq("cost_based_regime")].iloc[0]
                                full_pilot_cost = float(portfolio["npv_gross_fiscal_cost_pkr_m"])
                                full_pilot_incremental = float(portfolio["npv_incremental_assessed_income_pkr_m"])
                                full_pilot_admin_cost = float(portfolio["npv_admin_cost_pkr_m"])
                                full_pilot_review_hours = float(portfolio["review_workload_hours"])
                                full_pilot_peak_hours = float(portfolio.get("peak_annual_review_workload_hours", 0.0))
                                tested_cost = full_pilot_cost * uptake
                                tested_incremental = full_pilot_incremental * uptake
                                tested_admin_cost = full_pilot_admin_cost * uptake
                                tested_review_hours = full_pilot_review_hours * uptake
                                tested_peak_hours = full_pilot_peak_hours * uptake
                                feasible = tested_cost <= envelope
                                binding = _frontier_binding_constraint(annual, feasible, tested_cost, envelope)
                                tested_cost_per_incremental = (
                                    round(tested_cost / tested_incremental, 6) if tested_incremental else "Not estimable"
                                )
                                rows.append(
                                    {
                                        "additionality_case": case,
                                        "instrument_package": package,
                                        "instrument_package_label": INSTRUMENT_PACKAGES[package],
                                        "capex_deduction_rate": rate,
                                        "annual_cap_pkr_m": cap,
                                        "qualifying_threshold_pkr_m": threshold,
                                        "utilization_rate": utilization,
                                        "pilot_uptake_share": uptake,
                                        "npv_full_pilot_gross_fiscal_cost_pkr_m": round(full_pilot_cost, 4),
                                        "npv_full_pilot_incremental_assessed_income_pkr_m": round(full_pilot_incremental, 4),
                                        "npv_full_pilot_admin_cost_pkr_m": round(full_pilot_admin_cost, 4),
                                        "full_pilot_review_workload_hours": round(full_pilot_review_hours, 4),
                                        "npv_tested_fiscal_cost_pkr_m": round(tested_cost, 4),
                                        "npv_gross_fiscal_cost_pkr_m": round(tested_cost, 4),
                                        "fiscal_envelope_pkr_m": round(envelope, 4),
                                        "fiscal_envelope_definition": assumptions.fiscal_envelope_definition,
                                        "envelope_margin_pkr_m": round(envelope - tested_cost, 4),
                                        "feasible_flag": bool(feasible),
                                        "solver_status": "within_illustrative_D5_envelope" if feasible else "outside_illustrative_D5_envelope",
                                        "binding_constraint": binding,
                                        "npv_incremental_assessed_income_pkr_m": round(tested_incremental, 4),
                                        "npv_admin_cost_pkr_m": round(tested_admin_cost, 4),
                                        "review_workload_hours": round(tested_review_hours, 4),
                                        "peak_annual_review_workload_hours": round(tested_peak_hours, 4),
                                        "indicative_fte_requirement": round(tested_peak_hours / variant.annual_fte_hours, 6),
                                        "fiscal_cost_per_incremental_income": tested_cost_per_incremental,
                                        "duration_sunset": "Temporary only; no SEZ-specific incentive after 30 June 2035.",
                                        "model_version": MODEL_VERSION,
                                    }
                                )
    frontier = pd.DataFrame(rows)
    frontier["frontier_interpretation"] = _frontier_interpretation(frontier)
    return frontier


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
    """Compatibility wrapper: tests a single parameter against an explicit fiscal envelope."""

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
        return {"status": "no_feasible_setting_within_tested_range", "value": None, "cost_at_value": round(low_cost, 4)}
    if high_cost <= envelope + tolerance:
        return {"status": "no_binding_upper_bound_identified_within_tested_range", "value": None, "cost_at_value": round(high_cost, 4)}
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
    return {"status": "feasible_interior_frontier", "value": round(best, 6), "cost_at_value": round(best_cost, 4)}


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
            {
                "scenario_id": key,
                "scenario": value,
                "role": _scenario_role(key),
                "additionality_treatment": _scenario_additionality_text(key),
                "ordinary_cit_transition": _scenario_cit_transition_text(key),
                "d5_envelope_test": key in {"cost_based_regime", "combined_transition_pilot"},
                "fiscal_envelope_definition": assumptions.fiscal_envelope_definition,
                "model_version": MODEL_VERSION,
            }
            for key, value in SCENARIOS.items()
        ]
    )


def build_d7_handoff(parameter_ranges: pd.DataFrame, verification: pd.DataFrame, assumptions: CalibrationAssumptions) -> pd.DataFrame:
    evidence = "; ".join(verification["requirement"].dropna().astype(str).unique().tolist()) if not verification.empty else "Verification evidence not loaded"
    return pd.DataFrame(
        [
            {
                "trigger": "Fiscal cost exceeds approved envelope",
                "metric": "NPV gross fiscal cost vs approved D5 envelope",
                "threshold": "Above envelope in any semi-annual review",
                "review_frequency": "Semi-annual",
                "data_owner": "FBR / Finance Division",
                "decision_owner": "Task Force / Finance Division",
                "default_action": "Tighten or suspend",
                "parameter_potentially_affected": "Rate, cap, uptake, threshold, eligible instruments",
                "verification_evidence": evidence,
                "model_version": MODEL_VERSION,
            },
            {
                "trigger": "Verified additionality falls below agreed assumption",
                "metric": "Validated additionality vs D6 low/base/high assumption",
                "threshold": "Below low-case assumption or comparator evidence negative",
                "review_frequency": "Semi-annual",
                "data_owner": "BOI / SEZA / FBR / REMIT",
                "decision_owner": "Task Force / BOI",
                "default_action": "Recalibrate",
                "parameter_potentially_affected": "Instrument package, rate, eligibility, continuation",
                "verification_evidence": "Comparator evidence; enterprise questionnaire; FBR/sector data",
                "model_version": MODEL_VERSION,
            },
            {
                "trigger": "Claim-disallowance rate exceeds threshold",
                "metric": "Share of claimed deduction value disallowed after review",
                "threshold": ">20% by value or repeated documentation failures",
                "review_frequency": "Quarterly",
                "data_owner": "FBR / enterprise auditors",
                "decision_owner": "FBR / Finance Division",
                "default_action": "Tighten",
                "parameter_potentially_affected": "Verification rules, threshold, audit rate, carryforward",
                "verification_evidence": evidence,
                "model_version": MODEL_VERSION,
            },
            {
                "trigger": "Administrative backlog exceeds capacity",
                "metric": "Processing time, review hours, unresolved claims",
                "threshold": ">60 days median processing or >1.0 FTE gap",
                "review_frequency": "Quarterly",
                "data_owner": "BOI / FBR / SEZA",
                "decision_owner": "Task Force / BOI / FBR",
                "default_action": "Suspend new claims or simplify",
                "parameter_potentially_affected": "Eligible instruments, audit sample rate, threshold",
                "verification_evidence": "Claim register; review-hour logs; audit queue",
                "model_version": MODEL_VERSION,
            },
            {
                "trigger": "Uptake materially outside expected range",
                "metric": "Participating share vs expected pilot uptake",
                "threshold": "<25% or >125% of expected uptake",
                "review_frequency": "Quarterly",
                "data_owner": "BOI / SEZA",
                "decision_owner": "Task Force / BOI",
                "default_action": "Recalibrate",
                "parameter_potentially_affected": "Uptake assumption, cap, rate, outreach conditions",
                "verification_evidence": "Registration and claim uptake data",
                "model_version": MODEL_VERSION,
            },
            {
                "trigger": "Compliance or verification failure occurs",
                "metric": "Developer/enterprise compliance status and audit findings",
                "threshold": "Material breach, unresolved legal dispute, or failed audit",
                "review_frequency": "Continuous / quarterly",
                "data_owner": "SEZA / BOI / FBR / legal team",
                "decision_owner": "Task Force / legal authority / FBR",
                "default_action": "Suspend or terminate",
                "parameter_potentially_affected": "Eligibility, transition status, enforcement path",
                "verification_evidence": "Legal review; compliance file; audit report",
                "model_version": MODEL_VERSION,
            },
        ]
    )


def _blocked_frames(
    status: str,
    assumptions_frame: pd.DataFrame,
    scenario_definitions: pd.DataFrame,
    verification: pd.DataFrame,
    enterprises: pd.DataFrame | None = None,
    readiness: pd.DataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    status_df = pd.DataFrame(
        [
            {
                "calibration_status": status,
                "blocked_reason": "Enterprise-level financial evidence is required before D6 calculations can run.",
                "model_version": MODEL_VERSION,
            }
        ]
    )
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
    return pd.DataFrame(
        [
            {
                "assumption_key": field,
                "value": getattr(CalibrationAssumptions(), field),
                "unit": "",
                "provenance": "code default",
                "editable": True,
                "description": "",
            }
            for field in CalibrationAssumptions.__dataclass_fields__
        ]
    )


def _assumptions_from_frame(frame: pd.DataFrame) -> CalibrationAssumptions:
    values: dict[str, Any] = {}
    fields = CalibrationAssumptions.__dataclass_fields__
    string_keys = {"cohort_eligibility_policy", "instrument_package", "fiscal_envelope_definition"}
    for _, row in frame.iterrows():
        key = str(row.get("assumption_key", "")).strip()
        if key not in fields:
            continue
        raw = row.get("value")
        if clean_text(raw) == "":
            values[key] = None
        elif key in string_keys:
            values[key] = clean_text(raw)
        elif key.endswith("_year") or key.endswith("_years"):
            values[key] = int(float(raw))
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
        "d6_qualifying_threshold_pkr_m": "qualifying_expenditure_threshold_pkr_m",
        "d6_utilization_rate": "utilization_rate",
        "d6_discount_rate": "discount_rate",
        "d6_pilot_uptake_share": "pilot_uptake_share",
    }
    for source_key, target_key in numeric_keys.items():
        if source_key not in scenario:
            continue
        parsed = to_float(scenario.get(source_key))
        if parsed is not None:
            updates[target_key] = parsed

    package = clean_text(scenario.get("d6_instrument_package")).lower()
    if package in INSTRUMENT_PACKAGES:
        updates["instrument_package"] = package
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
                "instrument_package",
                "capex_deduction_rate",
                "annual_deduction_cap_pkr_m",
                "qualifying_expenditure_threshold_pkr_m",
                "utilization_rate",
                "discount_rate",
                "pilot_uptake_share",
            }
        )
    return out


def _empty_deduction_data() -> dict[str, Any]:
    return {
        "capex_incremental_deduction_pkr_m": 0.0,
        "ordinary_capex_depreciation_offset_pkr_m": 0.0,
        "rd_incremental_deduction_pkr_m": 0.0,
        "training_incremental_deduction_pkr_m": 0.0,
        "deduction_generated_before_utilization_pkr_m": 0.0,
        "deduction_generated_after_utilization_pkr_m": 0.0,
        "deduction_generated_pkr_m": 0.0,
        "deduction_used_pkr_m": 0.0,
        "carryforward_used_pkr_m": 0.0,
        "deduction_expired_pkr_m": 0.0,
        "closing_carryforward_pkr_m": 0.0,
        "current_year_potential_incentive_deduction_pkr_m": 0.0,
        "current_year_incentive_intensity_factor": 0.0,
        "threshold_met": False,
        "binding_constraint": "not_applicable",
    }


def _support_eligibility_status(row: pd.Series) -> str:
    if not bool(row.get("evidence_model_ready")):
        return "not_model_ready_for_calculation"
    if bool(row.get("epz_excluded")):
        return "excluded_epz_track"
    if not bool(row.get("legal_ready")):
        return "not_support_ready_pending_D4_legal_review"
    if not bool(row.get("fiscal_ready")):
        return "not_support_ready_pending_D5_FBR_validation"
    if not bool(row.get("compliance_ready")):
        return "not_support_ready_compliance_or_cure_required"
    additionality = clean_text(row.get("additionality_confidence")).lower()
    if additionality in {"", "unknown", "low"}:
        return "not_support_ready_additionality_not_established"
    return "potential_cost_based_review_input_subject_to_validation"


def _transition_treatment_status(row: pd.Series) -> str:
    if not bool(row.get("evidence_model_ready")):
        return "calculation_blocked"
    if _is_non_compliant(row):
        return "accelerated_removal_or_sanction_review"
    if not bool(row.get("legal_ready")):
        return "legal_transition_review"
    if clean_text(row.get("activity_category")).lower() == "moving_toward_production":
        return "construction_stage_transition_review"
    if _support_can_claim(row):
        return "cost_based_pilot_review_possible"
    return "ordinary_or_non_fiscal_transition_review"


def _blocked_reason(row: pd.Series) -> str:
    reasons = []
    if row.get("epz_excluded"):
        reasons.append("EPZ cohort excluded from default SEZ D6 calibration slice.")
    if not row.get("financial_evidence_complete"):
        reasons.append("Enterprise financial evidence incomplete for calculation.")
    if pd.isna(row.get("baseline_assessed_income_pkr_m")):
        reasons.append("Enterprise assessed-income basis missing.")
    if reasons:
        return " ".join(reasons)
    if not row.get("support_eligibility_status", "").startswith("potential"):
        return f"Synthetic model-ready, but support review is blocked: {row.get('support_eligibility_status')}."
    return "Synthetic model-ready for D6 calculation; real-world use still requires D4/D5/human validation."


def _support_can_claim(row: pd.Series | dict[str, Any]) -> bool:
    return clean_text(row.get("support_eligibility_status")).startswith("potential_cost_based_review_input")


def _is_non_compliant(row: pd.Series | dict[str, Any]) -> bool:
    values = [
        clean_text(row.get("compliance_status")).lower(),
        clean_text(row.get("developer_compliance_status")).lower(),
        clean_text(row.get("enterprise_compliance_status")).lower(),
    ]
    return any(value == "non_compliant" for value in values)


def _scenario_additionality_share(
    enterprise: pd.Series | dict[str, Any],
    assumptions: CalibrationAssumptions,
    scenario_id: str,
    additionality_case: str,
) -> float:
    if scenario_id == "no_sez_specific_incentive":
        return 0.0
    if scenario_id == "accelerated_removal" and _is_non_compliant(enterprise):
        return 0.0
    if scenario_id == "cost_based_regime" and not _support_can_claim(enterprise):
        return 0.0
    base = assumptions.additionality_share(additionality_case)
    confidence_factor = {
        "high": 1.0,
        "medium": 0.75,
        "low": 0.25,
        "unknown": 0.35,
        "": 0.35,
    }.get(clean_text(enterprise.get("additionality_confidence")).lower(), 0.5)
    if scenario_id in {"status_quo_to_2035", "accelerated_removal"}:
        return base * assumptions.status_quo_additionality_factor * confidence_factor
    return base * confidence_factor


def _responsive_expenditure(
    capex: float,
    rd: float,
    training: float,
    scenario_id: str,
    assumptions: CalibrationAssumptions,
    support_can_claim: bool,
) -> float:
    if scenario_id == "no_sez_specific_incentive":
        return 0.0
    if scenario_id in {"status_quo_to_2035", "accelerated_removal"}:
        return capex + rd + training
    if scenario_id == "cost_based_regime" and not support_can_claim:
        return 0.0
    package = clean_text(assumptions.instrument_package).lower() or "full"
    total = 0.0
    if package in {"full", "capex_only"}:
        total += capex
    if package in {"full", "rd_training"}:
        total += rd + training
    return total


def _incentive_signal(
    capex: float,
    rd: float,
    training: float,
    scenario_id: str,
    assumptions: CalibrationAssumptions,
    support_can_claim: bool,
) -> dict[str, Any]:
    selected_expenditure = _responsive_expenditure(capex, rd, training, scenario_id, assumptions, support_can_claim)
    if selected_expenditure <= 0:
        return {
            "responsive_expenditure_pkr_m": 0.0,
            "potential_incentive_deduction_pkr_m": 0.0,
            "incentive_intensity_factor": 0.0,
            "incentive_availability_status": "no_incentive_available",
        }
    if scenario_id in {"status_quo_to_2035", "accelerated_removal"}:
        return {
            "responsive_expenditure_pkr_m": selected_expenditure,
            "potential_incentive_deduction_pkr_m": 0.0,
            "incentive_intensity_factor": 1.0,
            "incentive_availability_status": "legacy_incentive_available_until_sunset",
        }
    if scenario_id != "cost_based_regime":
        return {
            "responsive_expenditure_pkr_m": 0.0,
            "potential_incentive_deduction_pkr_m": 0.0,
            "incentive_intensity_factor": 0.0,
            "incentive_availability_status": "not_applicable",
        }

    signal = _cost_based_incentive_signal(capex, rd, training, assumptions)
    potential_deduction = signal["potential_incentive_deduction_pkr_m"]
    if potential_deduction <= 0:
        return {
            "responsive_expenditure_pkr_m": 0.0,
            "potential_incentive_deduction_pkr_m": 0.0,
            "incentive_intensity_factor": 0.0,
            "incentive_availability_status": signal["incentive_availability_status"],
        }
    return {
        "responsive_expenditure_pkr_m": signal["responsive_expenditure_pkr_m"],
        "potential_incentive_deduction_pkr_m": potential_deduction,
        "incentive_intensity_factor": signal["incentive_intensity_factor"],
        "incentive_availability_status": signal["incentive_availability_status"],
    }


def _cost_based_incentive_signal(
    capex: float,
    rd: float,
    training: float,
    assumptions: CalibrationAssumptions,
) -> dict[str, Any]:
    package = clean_text(assumptions.instrument_package).lower() or "full"
    ordinary_offset = capex / max(assumptions.ordinary_capex_depreciation_years, 1)
    threshold = max(0.0, assumptions.qualifying_expenditure_threshold_pkr_m)
    total_qualifying = capex + rd + training
    threshold_met = total_qualifying >= threshold

    selected_components = {"capex": 0.0, "rd": 0.0, "training": 0.0}
    gross_components = {"capex": 0.0, "rd": 0.0, "training": 0.0}
    if threshold_met:
        if package in {"full", "capex_only"}:
            selected_components["capex"] = capex
            gross_components["capex"] = max(0.0, capex * max(0.0, assumptions.capex_deduction_rate) - ordinary_offset)
        if package in {"full", "rd_training"}:
            selected_components["rd"] = rd
            selected_components["training"] = training
            gross_components["rd"] = max(0.0, rd * (assumptions.rd_super_deduction_total_rate - 1.0))
            gross_components["training"] = max(0.0, training * (assumptions.training_super_deduction_total_rate - 1.0))

    generated_before_utilization = sum(gross_components.values())
    utilization = min(max(float(assumptions.utilization_rate), 0.0), 1.0)
    generated_after_utilization = generated_before_utilization * utilization
    annual_cap = max(0.0, assumptions.annual_deduction_cap_pkr_m)
    generated = min(generated_after_utilization, annual_cap)

    allocation_factor = safe_divide(generated, generated_after_utilization) or 0.0
    responsive_expenditure = 0.0
    for key, gross_deduction in gross_components.items():
        selected = selected_components[key]
        available_component_deduction = gross_deduction * utilization * allocation_factor
        responsive_expenditure += min(selected, available_component_deduction)

    selected_expenditure = sum(selected_components.values())
    intensity = safe_divide(responsive_expenditure, selected_expenditure) or 0.0
    if not threshold_met:
        status = "qualifying_threshold_blocks_incentive"
    elif generated_before_utilization <= 0:
        status = "no_eligible_incremental_deduction"
    elif generated <= 0 and utilization <= 0:
        status = "utilization_zero_blocks_incentive"
    elif generated <= 0 and annual_cap <= 0:
        status = "annual_cap_zero_blocks_incentive"
    else:
        status = "positive_incentive_available"

    return {
        "capex_incremental_deduction_pkr_m": gross_components["capex"],
        "ordinary_capex_depreciation_offset_pkr_m": ordinary_offset,
        "rd_incremental_deduction_pkr_m": gross_components["rd"],
        "training_incremental_deduction_pkr_m": gross_components["training"],
        "deduction_generated_before_utilization_pkr_m": generated_before_utilization,
        "deduction_generated_after_utilization_pkr_m": generated_after_utilization,
        "potential_incentive_deduction_pkr_m": generated,
        "responsive_expenditure_pkr_m": responsive_expenditure,
        "incentive_intensity_factor": min(max(intensity, 0.0), 1.0),
        "threshold_met": bool(threshold_met),
        "incentive_availability_status": status,
    }


def _administrative_cost(
    deduction_data: dict[str, Any],
    assumptions: CalibrationAssumptions,
    enterprise: pd.Series | dict[str, Any],
) -> tuple[float, float, float]:
    has_claim = bool(deduction_data.get("deduction_generated_pkr_m", 0.0) or deduction_data.get("carryforward_used_pkr_m", 0.0))
    if not has_claim:
        return 0.0, 0.0, 0.0
    burden_multiplier = {
        "high": 1.25,
        "medium": 1.0,
        "low": 0.8,
    }.get(clean_text(enterprise.get("data_confidence_band")).lower(), 1.0)
    hours = (assumptions.admin_review_hours_per_claim + assumptions.admin_audit_hours_per_claim * assumptions.audit_sample_rate) * burden_multiplier
    cost = assumptions.fixed_admin_cost_per_claim_pkr_m + hours * assumptions.admin_cost_per_review_hour_pkr_m
    cost += assumptions.admin_cost_per_enterprise_pkr_m
    return cost, hours, hours / assumptions.annual_fte_hours


def _deduction_binding_constraint(
    threshold_met: bool,
    generated_before_utilization: float,
    generated_after_utilization: float,
    generated: float,
    used: float,
    closing: float,
    assumptions: CalibrationAssumptions,
) -> str:
    if not threshold_met:
        return "qualifying_threshold"
    if generated_before_utilization <= 0:
        return "no_eligible_incremental_deduction"
    if generated < generated_after_utilization - 1e-6:
        return "annual_cap"
    if assumptions.utilization_rate < 0.999:
        return "utilization_rate"
    if closing > 1e-6 and used < generated:
        return "taxable_income_capacity_or_carryforward"
    return "not_binding_within_enterprise_year"


def _frontier_binding_constraint(annual: pd.DataFrame, feasible: bool, cost: float, envelope: float) -> str:
    if cost <= 1e-9:
        return "no_pilot_uptake_or_no_available_incentive"
    if not feasible:
        return "fiscal_envelope"
    if abs(envelope - cost) <= max(50.0, envelope * 0.01):
        return "fiscal_envelope_near_binding"
    constraints = annual.get("binding_constraint", pd.Series(dtype=str)).astype(str)
    if constraints.str.contains("annual_cap").any():
        return "annual_cap"
    if constraints.str.contains("qualifying_threshold").any():
        return "qualifying_threshold"
    if constraints.str.contains("utilization_rate").any():
        return "utilization_rate"
    return "no_binding_upper_bound_identified_within_tested_range"


def _frontier_interpretation(frontier: pd.DataFrame) -> pd.Series:
    if frontier.empty:
        return pd.Series(dtype=str)
    any_feasible = frontier["feasible_flag"].astype(bool).any()
    any_infeasible = (~frontier["feasible_flag"].astype(bool)).any()
    if any_feasible and any_infeasible:
        text = "Feasible parameter frontier: the illustrative D5 fiscal envelope binds within the tested range."
    elif any_feasible:
        text = "No binding upper bound identified within the tested range."
    else:
        text = "No feasible setting within the tested range."
    return pd.Series([text] * len(frontier), index=frontier.index)


def _weighted_npv(group: pd.DataFrame, column: str) -> float:
    if column not in group.columns:
        return 0.0
    return float((group[column] * group["aggregation_weight"] * group["discount_factor"]).sum())


def _fiscal_envelope(annual: pd.DataFrame, assumptions: CalibrationAssumptions) -> float:
    if assumptions.d5_fiscal_envelope_pkr_m is not None:
        return float(assumptions.d5_fiscal_envelope_pkr_m)
    if annual.empty or "scenario_id" not in annual.columns:
        return 0.0
    status = annual[(annual["scenario_id"] == "status_quo_to_2035") & (annual["additionality_case"] == "base")]
    if status.empty:
        return 0.0
    return _weighted_npv(status, "gross_fiscal_cost_pkr_m")


def _fiscal_envelope_type(assumptions: CalibrationAssumptions) -> str:
    return "illustrative_D5_fiscal_envelope" if assumptions.d5_fiscal_envelope_pkr_m is not None else "synthetic_proxy_status_quo"


def _scenario_role(scenario_id: str) -> str:
    return {
        "no_sez_specific_incentive": "Ordinary-reference counterfactual with no SEZ-specific deduction and no incentive-caused incremental activity.",
        "status_quo_to_2035": "Protected current treatment through natural expiry or June 2035 hard cap.",
        "accelerated_removal": "Earlier removal for data-complete non-compliant enterprises; compliant records remain on status quo.",
        "cost_based_regime": "Ordinary CIT plus temporary CAPEX/R&D/training deductions for support-review-ready synthetic records only.",
        "combined_transition_pilot": "Blends non-pilot treatment and pilot cost-based treatment by explicit uptake share.",
    }[scenario_id]


def _scenario_additionality_text(scenario_id: str) -> str:
    return {
        "no_sez_specific_incentive": "No incentive-caused incremental income is added to the reference path.",
        "status_quo_to_2035": "Uses a reduced synthetic status-quo additionality factor; not a causal estimate.",
        "accelerated_removal": "Non-compliant records receive no incentive-caused incremental income after removal.",
        "cost_based_regime": "Uses low/base/high synthetic response assumptions by instrument package and support-readiness status.",
        "combined_transition_pilot": "Blends non-pilot and full-pilot additionality consequences by uptake share.",
    }[scenario_id]


def _scenario_cit_transition_text(scenario_id: str) -> str:
    if scenario_id == "cost_based_regime":
        return "No hidden CIT phase-in; ordinary statutory CIT applies before cost-based deductions."
    if scenario_id == "status_quo_to_2035":
        return "CIT holiday/protected exemption retained to the 2035 cap where assumed."
    if scenario_id == "accelerated_removal":
        return "Non-compliant records move to ordinary statutory CIT; no reduced-CIT phase-in is applied."
    return "Ordinary statutory CIT."


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
