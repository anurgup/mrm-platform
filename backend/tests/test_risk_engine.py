"""
Tests for the deterministic risk engine (app/engines/risk.py).

NOTE on boundary tests: the spec asked for "exactly 39 -> LOW" and
"exactly 69 -> MEDIUM" as the values just below the MEDIUM (40) and HIGH (70)
thresholds. Both are mathematically unreachable: every rule's points (30, 25,
10, 20, 20, 10, 20) is a multiple of 5, so every possible total score is too
(confirmed by exhaustively enumerating all 6*5*4*2=240 valid input
combinations — the full achievable score set is
{10,20,25,30,35,40,45,50,55,60,65,70}). 35 and 65 are the nearest reachable
values below each threshold, so those are what's tested here instead.
"""

import itertools

import pytest

from app.engines.risk import RiskInput, assess
from app.models.enums import (
    BusinessFunction,
    DataClassification,
    ModelType,
    RiskCategory,
    VendorDependency,
)


def _input(
    business_function: BusinessFunction = BusinessFunction.RISK_ANALYTICS,
    model_type: ModelType = ModelType.RULE_BASED_ENGINE,
    data_classification: DataClassification = DataClassification.PUBLIC,
    vendor_dependency: VendorDependency = VendorDependency.INTERNAL,
) -> RiskInput:
    return RiskInput(
        business_function=business_function,
        model_type=model_type,
        data_classification=data_classification,
        vendor_dependency=vendor_dependency,
    )


# ---- Boundary tests ----

def test_score_35_is_low() -> None:
    # CUSTOMER_SERVICE (+25) + MACHINE_LEARNING (+10), no sensitive data, no
    # vendor = 35 — nearest reachable value below the 40 MEDIUM threshold.
    result = assess(_input(
        business_function=BusinessFunction.CUSTOMER_SERVICE,
        model_type=ModelType.MACHINE_LEARNING,
        data_classification=DataClassification.PUBLIC,
        vendor_dependency=VendorDependency.INTERNAL,
    ))
    assert result.score == 35
    assert result.category == RiskCategory.LOW


def test_score_40_is_medium() -> None:
    # RISK_ANALYTICS (+10) + CONFIDENTIAL (+20) + MACHINE_LEARNING (+10) = 40.
    result = assess(_input(
        business_function=BusinessFunction.RISK_ANALYTICS,
        model_type=ModelType.MACHINE_LEARNING,
        data_classification=DataClassification.CONFIDENTIAL,
        vendor_dependency=VendorDependency.INTERNAL,
    ))
    assert result.score == 40
    assert result.category == RiskCategory.MEDIUM


def test_score_65_is_medium() -> None:
    # CUSTOMER_SERVICE (+25) + THIRD_PARTY_AI_API (complexity +0) +
    # RESTRICTED (+20) + EXTERNAL_VENDOR (+20) = 65 — nearest reachable
    # value below the 70 HIGH threshold.
    result = assess(_input(
        business_function=BusinessFunction.CUSTOMER_SERVICE,
        model_type=ModelType.THIRD_PARTY_AI_API,
        data_classification=DataClassification.RESTRICTED,
        vendor_dependency=VendorDependency.EXTERNAL_VENDOR,
    ))
    assert result.score == 65
    assert result.category == RiskCategory.MEDIUM


def test_score_70_is_high() -> None:
    # FRAUD_DETECTION (+30) + THIRD_PARTY_AI_API (complexity +0) +
    # RESTRICTED (+20) + EXTERNAL_VENDOR (+20) = 70.
    result = assess(_input(
        business_function=BusinessFunction.FRAUD_DETECTION,
        model_type=ModelType.THIRD_PARTY_AI_API,
        data_classification=DataClassification.RESTRICTED,
        vendor_dependency=VendorDependency.EXTERNAL_VENDOR,
    ))
    assert result.score == 70
    assert result.category == RiskCategory.HIGH


# ---- Per-rule tests ----

BUSINESS_IMPACT_EXPECTED = {
    BusinessFunction.LOAN_UNDERWRITING: 30,
    BusinessFunction.FRAUD_DETECTION: 30,
    BusinessFunction.COLLECTIONS: 30,
    BusinessFunction.CUSTOMER_SERVICE: 25,
    BusinessFunction.DOCUMENT_PROCESSING: 10,
    BusinessFunction.RISK_ANALYTICS: 10,
}


@pytest.mark.parametrize("business_function,expected_points", BUSINESS_IMPACT_EXPECTED.items())
def test_business_impact_tier_yields_right_points_and_only_one_fires(
    business_function: BusinessFunction, expected_points: int
) -> None:
    result = assess(_input(business_function=business_function))
    impact_entries = [f for f in result.factor_breakdown if f.key.startswith("business_impact_")]
    assert len(impact_entries) == 1
    assert impact_entries[0].points == expected_points


COMPLEXITY_EXPECTED = {
    ModelType.GENERATIVE_AI: 20,
    ModelType.DEEP_LEARNING: 20,
    ModelType.MACHINE_LEARNING: 10,
    ModelType.RULE_BASED_ENGINE: 0,
    ModelType.THIRD_PARTY_AI_API: 0,
}


@pytest.mark.parametrize("model_type,expected_points", COMPLEXITY_EXPECTED.items())
def test_complexity_tier_yields_right_points_and_at_most_one_fires(
    model_type: ModelType, expected_points: int
) -> None:
    result = assess(_input(model_type=model_type))
    complexity_entries = [f for f in result.factor_breakdown if f.key.startswith("complexity_")]
    if expected_points == 0:
        assert complexity_entries == []
    else:
        assert len(complexity_entries) == 1
        assert complexity_entries[0].points == expected_points


@pytest.mark.parametrize("data_classification,expect_fires", [
    (DataClassification.PUBLIC, False),
    (DataClassification.INTERNAL, False),
    (DataClassification.CONFIDENTIAL, True),
    (DataClassification.RESTRICTED, True),
])
def test_data_sensitivity_adds_20_only_for_confidential_restricted(
    data_classification: DataClassification, expect_fires: bool
) -> None:
    result = assess(_input(data_classification=data_classification))
    sensitivity_entries = [
        f for f in result.factor_breakdown if f.key == "data_sensitivity_financial_customer"
    ]
    if expect_fires:
        assert len(sensitivity_entries) == 1
        assert sensitivity_entries[0].points == 20
    else:
        assert sensitivity_entries == []


@pytest.mark.parametrize("model_type,vendor_dependency,expect_fires", [
    (ModelType.THIRD_PARTY_AI_API, VendorDependency.EXTERNAL_VENDOR, True),
    (ModelType.THIRD_PARTY_AI_API, VendorDependency.INTERNAL, False),
    (ModelType.MACHINE_LEARNING, VendorDependency.EXTERNAL_VENDOR, False),
    (ModelType.MACHINE_LEARNING, VendorDependency.INTERNAL, False),
])
def test_vendor_blackbox_adds_20_only_for_external_third_party(
    model_type: ModelType, vendor_dependency: VendorDependency, expect_fires: bool
) -> None:
    result = assess(_input(model_type=model_type, vendor_dependency=vendor_dependency))
    vendor_entries = [f for f in result.factor_breakdown if f.key == "vendor_blackbox_external"]
    if expect_fires:
        assert len(vendor_entries) == 1
        assert vendor_entries[0].points == 20
    else:
        assert vendor_entries == []


def test_rule_based_engine_internal_model_on_public_data_scores_near_floor() -> None:
    # Business impact always contributes something (every BusinessFunction
    # value matches exactly one of the three business-impact rules), so 10
    # (internal analytics, the lowest tier) is the engine's actual floor —
    # not 0.
    result = assess(_input(
        business_function=BusinessFunction.RISK_ANALYTICS,
        model_type=ModelType.RULE_BASED_ENGINE,
        data_classification=DataClassification.PUBLIC,
        vendor_dependency=VendorDependency.INTERNAL,
    ))
    assert result.score == 10
    assert result.category == RiskCategory.LOW


# ---- Invariant tests ----

def test_determinism_same_input_twice_returns_equal_results() -> None:
    risk_input = _input(
        business_function=BusinessFunction.LOAN_UNDERWRITING,
        model_type=ModelType.GENERATIVE_AI,
        data_classification=DataClassification.RESTRICTED,
        vendor_dependency=VendorDependency.EXTERNAL_VENDOR,
    )
    assert assess(risk_input) == assess(risk_input)


def test_breakdown_sum_equals_score_for_every_valid_input() -> None:
    """Exhaustive, not sampled — the input space is only 6*5*4*2=240 valid
    combinations, so cover all of them rather than a random subset."""
    for business_function, model_type, data_classification, vendor_dependency in itertools.product(
        BusinessFunction, ModelType, DataClassification, VendorDependency
    ):
        result = assess(_input(
            business_function=business_function,
            model_type=model_type,
            data_classification=data_classification,
            vendor_dependency=vendor_dependency,
        ))
        assert sum(f.points for f in result.factor_breakdown) == result.score
        assert all(f.reason for f in result.factor_breakdown)


def test_factor_breakdown_has_a_reason_for_every_contribution() -> None:
    result = assess(_input(
        business_function=BusinessFunction.FRAUD_DETECTION,
        model_type=ModelType.THIRD_PARTY_AI_API,
        data_classification=DataClassification.RESTRICTED,
        vendor_dependency=VendorDependency.EXTERNAL_VENDOR,
    ))
    assert len(result.factor_breakdown) > 0
    for factor in result.factor_breakdown:
        assert factor.reason.strip() != ""


# ---- Worked examples ----

def test_worked_example_credit_underwriting_scorecard() -> None:
    # Loan Underwriting (+30), Restricted data (+20), Machine Learning (+10) = 60 -> MEDIUM.
    result = assess(_input(
        business_function=BusinessFunction.LOAN_UNDERWRITING,
        model_type=ModelType.MACHINE_LEARNING,
        data_classification=DataClassification.RESTRICTED,
        vendor_dependency=VendorDependency.INTERNAL,
    ))
    assert result.score == 60
    assert result.category == RiskCategory.MEDIUM


def test_worked_example_high_risk_vendor_fraud_model() -> None:
    # Fraud Detection (+30) + Third Party AI API external vendor (+20) +
    # Restricted (+20) = 70 -> HIGH.
    result = assess(_input(
        business_function=BusinessFunction.FRAUD_DETECTION,
        model_type=ModelType.THIRD_PARTY_AI_API,
        data_classification=DataClassification.RESTRICTED,
        vendor_dependency=VendorDependency.EXTERNAL_VENDOR,
    ))
    assert result.score == 70
    assert result.category == RiskCategory.HIGH
