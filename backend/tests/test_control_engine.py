from dataclasses import replace

import pytest

from app.engines.control import (
    TIER_CHECKLISTS,
    ControlInput,
    RegulatoryReference,
    evaluate,
)
from app.models.enums import RiskCategory, Severity
from app.services.regulatory_seed import SEED_MAPPINGS

FAKE_REFERENCES: dict[str, RegulatoryReference] = {
    "documentation": {
        "regulation_name": "RBI Master Direction on IT Governance, Risk, Controls and Assurance Practices",
        "reference_text": "Adequate documentation is expected for supervisory review.",
        "guidance_type": "BINDING",
        "effective_note": "IT Governance Master Direction",
    },
    "independent_validation": {
        "regulation_name": "RBI Scale Based Regulation (SBR) Framework",
        "reference_text": "Model validation independence is expected for material models.",
        "guidance_type": "BINDING",
        "effective_note": "Scale Based Regulation framework for NBFCs",
    },
    "explainability": {
        "regulation_name": "RBI FREE-AI Committee — Framework for Responsible and Ethical Enablement of AI",
        "reference_text": "Explainability and transparency of AI-driven decisions is emphasised.",
        "guidance_type": "EMERGING",
        "effective_note": "Committee framework — emerging guidance, not a binding direction",
    },
    "drift_monitoring": {
        "regulation_name": "RBI FREE-AI Committee — Framework for Responsible and Ethical Enablement of AI",
        "reference_text": "Ongoing monitoring of AI model behaviour and drift is expected.",
        "guidance_type": "EMERGING",
        "effective_note": "Committee framework — emerging guidance, not a binding direction",
    },
    "human_override": {
        "regulation_name": "RBI Guidelines on Digital Lending",
        "reference_text": "A human accountable owner is expected for credit decisioning.",
        "guidance_type": "BINDING",
        "effective_note": "Digital Lending Guidelines",
    },
    "audit_logging": {
        "regulation_name": "RBI Master Direction on IT Governance, Risk, Controls and Assurance Practices",
        "reference_text": "Audit logging and traceability is expected for critical systems.",
        "guidance_type": "BINDING",
        "effective_note": "IT Governance Master Direction",
    },
}


def fake_resolve(control_key: str) -> RegulatoryReference | None:
    return FAKE_REFERENCES.get(control_key)


def _all_present_input(risk_category: RiskCategory) -> ControlInput:
    return ControlInput(
        risk_category=risk_category,
        has_documentation=True,
        has_independent_validation=True,
        has_explainability=True,
        has_drift_monitoring=True,
        has_human_override=True,
        has_audit_logging=True,
        has_deployment_approval=True,
        has_model_owner=True,
        has_risk_owner=True,
    )


# ---- control_key alignment with P-1.3 (definition of done item 3) ----

def test_mapped_control_keys_exactly_match_p1_3_seed_minus_vendor_risk() -> None:
    seed_keys = {row["control_key"] for row in SEED_MAPPINGS}
    engine_mapped_keys = {
        "documentation", "independent_validation", "explainability",
        "drift_monitoring", "human_override", "audit_logging",
    }
    assert engine_mapped_keys == seed_keys - {"vendor_risk"}


# ---- Tier coverage ----

def test_high_model_all_nine_controls_present_passes() -> None:
    result = evaluate(_all_present_input(RiskCategory.HIGH), fake_resolve)
    assert result.overall_status == "PASS"
    assert result.finding_drafts == []
    assert result.controls_required == 9
    assert result.controls_passed == 9


def test_high_model_missing_independent_validation_produces_high_severity_finding() -> None:
    control_input = replace(_all_present_input(RiskCategory.HIGH), has_independent_validation=False)
    result = evaluate(control_input, fake_resolve)

    assert result.overall_status == "FAIL"
    assert len(result.finding_drafts) == 1
    draft = result.finding_drafts[0]
    assert draft.control_key == "independent_validation"
    assert draft.severity == Severity.HIGH
    assert draft.regulatory_reference == FAKE_REFERENCES["independent_validation"]


def test_high_model_missing_model_owner_has_no_regulatory_reference_and_does_not_crash() -> None:
    control_input = replace(_all_present_input(RiskCategory.HIGH), has_model_owner=False)
    result = evaluate(control_input, fake_resolve)

    assert result.overall_status == "FAIL"
    draft = next(d for d in result.finding_drafts if d.control_key == "model_owner")
    assert draft.regulatory_reference is None


def test_medium_model_missing_drift_monitoring_fails_with_medium_severity() -> None:
    control_input = replace(_all_present_input(RiskCategory.MEDIUM), has_drift_monitoring=False)
    result = evaluate(control_input, fake_resolve)

    assert result.controls_required == 4
    assert result.overall_status == "FAIL"
    draft = next(d for d in result.finding_drafts if d.control_key == "drift_monitoring")
    assert draft.severity == Severity.MEDIUM
    assert draft.regulatory_reference == FAKE_REFERENCES["drift_monitoring"]


def test_low_model_with_owner_and_documentation_passes() -> None:
    result = evaluate(_all_present_input(RiskCategory.LOW), fake_resolve)
    assert result.controls_required == 2
    assert result.overall_status == "PASS"
    assert result.passed_controls == ["model_owner", "documentation"]


@pytest.mark.parametrize("risk_category,expected_count", [
    (RiskCategory.HIGH, 9),
    (RiskCategory.MEDIUM, 4),
    (RiskCategory.LOW, 2),
])
def test_controls_required_matches_tier_size(
    risk_category: RiskCategory, expected_count: int
) -> None:
    assert len(TIER_CHECKLISTS[risk_category]) == expected_count
    result = evaluate(_all_present_input(risk_category), fake_resolve)
    assert result.controls_required == expected_count


# ---- Invariants ----

def test_determinism_same_input_twice_returns_equal_results() -> None:
    control_input = replace(_all_present_input(RiskCategory.HIGH), has_explainability=False)
    assert evaluate(control_input, fake_resolve) == evaluate(control_input, fake_resolve)


def test_overall_status_pass_iff_finding_drafts_empty() -> None:
    passing = evaluate(_all_present_input(RiskCategory.HIGH), fake_resolve)
    assert passing.overall_status == "PASS"
    assert passing.finding_drafts == []

    failing = evaluate(
        replace(_all_present_input(RiskCategory.HIGH), has_audit_logging=False), fake_resolve
    )
    assert failing.overall_status == "FAIL"
    assert len(failing.finding_drafts) > 0


def test_every_finding_draft_is_a_required_control_whose_attestation_was_false() -> None:
    control_input = ControlInput(
        risk_category=RiskCategory.HIGH,
        has_documentation=False,
        has_independent_validation=False,
        has_explainability=True,
        has_drift_monitoring=False,
        has_human_override=True,
        has_audit_logging=True,
        has_deployment_approval=True,
        has_model_owner=True,
        has_risk_owner=True,
    )
    result = evaluate(control_input, fake_resolve)
    required = set(TIER_CHECKLISTS[RiskCategory.HIGH])
    draft_keys = {d.control_key for d in result.finding_drafts}
    assert draft_keys <= required
    assert draft_keys == {"documentation", "independent_validation", "drift_monitoring"}


# ---- Worked example ----

def test_worked_example_fraud_detection_vendor_api() -> None:
    # HIGH tier, missing independent_validation AND explainability -> FAIL,
    # exactly two drafts, both HIGH severity, both with a regulatory reference.
    control_input = replace(
        _all_present_input(RiskCategory.HIGH),
        has_independent_validation=False,
        has_explainability=False,
    )
    result = evaluate(control_input, fake_resolve)

    assert result.overall_status == "FAIL"
    assert len(result.finding_drafts) == 2
    assert {d.control_key for d in result.finding_drafts} == {
        "independent_validation", "explainability",
    }
    for draft in result.finding_drafts:
        assert draft.severity == Severity.HIGH
        assert draft.regulatory_reference is not None
