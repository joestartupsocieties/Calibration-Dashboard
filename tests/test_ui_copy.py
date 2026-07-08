from pathlib import Path

from sez_calibration.ui_copy import (
    APP_SUBTITLE,
    APP_TITLE,
    BANNED_VISIBLE_TERMS,
    DATA_PROFILE_LABEL,
    DATASET_BASIS_LABEL,
    HUMAN_REVIEW_LABEL,
    NON_DECISION_STATEMENT,
    REAL_USE_REQUIREMENTS,
)


def default_visible_copy() -> str:
    return "\n".join(
        [
            APP_TITLE,
            APP_SUBTITLE,
            DATA_PROFILE_LABEL,
            DATASET_BASIS_LABEL,
            HUMAN_REVIEW_LABEL,
            NON_DECISION_STATEMENT,
            REAL_USE_REQUIREMENTS,
        ]
    )


def test_ui_copy_has_required_guardrails():
    assert APP_TITLE == "SEZ Incentive Transition Triage"
    assert DATA_PROFILE_LABEL == "Synthetic demo view"
    assert HUMAN_REVIEW_LABEL == "Human review required"
    assert DATASET_BASIS_LABEL == "Structured screening dataset"
    assert "workflow demonstration" in NON_DECISION_STATEMENT
    assert "does not approve incentives" in NON_DECISION_STATEMENT
    assert "set tax rates" in NON_DECISION_STATEMENT
    assert "determine fiscal cost" in NON_DECISION_STATEMENT
    for authority in ["BOI", "FBR", "Finance Division", "SEZA", "Law Division", "IMF"]:
        assert authority in NON_DECISION_STATEMENT
    assert "fiscal modeller" in NON_DECISION_STATEMENT
    assert "legal counsel review" in NON_DECISION_STATEMENT
    assert "D4 legal review" in REAL_USE_REQUIREMENTS
    assert "D5/FBR fiscal verification" in REAL_USE_REQUIREMENTS
    assert APP_SUBTITLE


def test_ui_copy_avoids_banned_terms():
    public_copy = default_visible_copy().lower()
    for term in BANNED_VISIBLE_TERMS:
        assert term.lower() not in public_copy


def test_scenario_settings_are_developer_gated_from_default_nav():
    repo_root = Path(__file__).resolve().parents[1]
    app_text = (repo_root / "app.py").read_text(encoding="utf-8")
    recommendation_engine_text = (repo_root / "src/sez_calibration/recommendation_engine.py").read_text(
        encoding="utf-8"
    )

    default_pages_block = app_text.split("PAGES = [", 1)[1].split("]", 1)[0]
    assert '"Scenario Settings"' not in default_pages_block
    assert "if SHOW_ADVANCED_SCENARIOS:" in app_text
    assert 'PAGES.append("Scenario Settings")' in app_text
    assert "Advanced Model Settings" not in app_text
    assert "Scenario Settings require" not in recommendation_engine_text
