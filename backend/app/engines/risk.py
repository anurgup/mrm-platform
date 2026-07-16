"""
Deterministic model risk scoring engine.

PURITY CONTRACT: assess() is a pure function. No database access, no I/O, no
randomness, no clock. Identical RiskInput -> byte-identical RiskResult, every
time. This is deliberate: a CRO must be able to ask "why did this model score
75?" and get an identical, itemized answer on every run. Persistence (writing
a RiskAssessment row) and adapting an AIModel ORM object into a RiskInput both
belong to the service layer (P-1.2), not here.

Rules live as DATA — the RULES list below — not as scattered if-statements.
This is what makes factor_breakdown fall out for free, and what will let
rules become configurable later without touching engine logic.

MUTUALLY-EXCLUSIVE GROUPS (read this before changing a rule):
Business Impact and Algorithm Complexity are each a group of rules where only
the HIGHEST-SCORING matching rule counts — they are not independent adds. A
model whose business_function matches "financial decision" does NOT also
score "internal analytics" on top; only +30 applies, not +30+10. Rules are
tagged with a `group` string; `assess()` resolves each group down to its best
match before summing. Rules with `group=None` (data sensitivity, vendor
dependency) are independent and always add on top when their predicate fires.
Conflating a mutually-exclusive group with independent adds is the single
most common way to get this score wrong.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from app.models.enums import (
    BusinessFunction,
    DataClassification,
    ModelType,
    RiskCategory,
    VendorDependency,
)

HIGH_THRESHOLD = 70
MEDIUM_THRESHOLD = 40


@dataclass(frozen=True)
class RiskInput:
    """The small typed input the engine actually needs — not an AIModel ORM
    object, so the engine is testable with zero database involvement."""

    business_function: BusinessFunction
    model_type: ModelType
    data_classification: DataClassification
    vendor_dependency: VendorDependency


@dataclass(frozen=True)
class FactorContribution:
    key: str
    reason: str
    points: int


@dataclass(frozen=True)
class RiskResult:
    score: int
    category: RiskCategory
    factor_breakdown: list[FactorContribution]
    explanation: str


@dataclass(frozen=True)
class Rule:
    key: str
    reason: str
    points: int
    predicate: Callable[[RiskInput], bool]
    group: str | None = field(default=None)


def _is_financial_decision(x: RiskInput) -> bool:
    return x.business_function in {
        BusinessFunction.LOAN_UNDERWRITING,
        BusinessFunction.FRAUD_DETECTION,
        BusinessFunction.COLLECTIONS,
    }


def _is_customer_facing(x: RiskInput) -> bool:
    return x.business_function == BusinessFunction.CUSTOMER_SERVICE


def _is_internal_analytics(x: RiskInput) -> bool:
    return x.business_function in {
        BusinessFunction.DOCUMENT_PROCESSING,
        BusinessFunction.RISK_ANALYTICS,
    }


def _is_sensitive_data(x: RiskInput) -> bool:
    return x.data_classification in {DataClassification.CONFIDENTIAL, DataClassification.RESTRICTED}


def _is_generative_ai(x: RiskInput) -> bool:
    return x.model_type == ModelType.GENERATIVE_AI


def _is_deep_learning(x: RiskInput) -> bool:
    return x.model_type == ModelType.DEEP_LEARNING


def _is_traditional_ml(x: RiskInput) -> bool:
    return x.model_type == ModelType.MACHINE_LEARNING


def _is_external_blackbox_vendor(x: RiskInput) -> bool:
    return (
        x.vendor_dependency == VendorDependency.EXTERNAL_VENDOR
        and x.model_type == ModelType.THIRD_PARTY_AI_API
    )


RULES: list[Rule] = [
    # --- Business Impact: mutually exclusive, highest applicable only ---
    Rule("business_impact_financial", "financial decision", 30, _is_financial_decision,
         group="business_impact"),
    Rule("business_impact_customer_facing", "customer facing", 25, _is_customer_facing,
         group="business_impact"),
    Rule("business_impact_internal_analytics", "internal analytics", 10, _is_internal_analytics,
         group="business_impact"),
    # --- Data Sensitivity: independent add ---
    Rule("data_sensitivity_financial_customer", "financial/customer data", 20, _is_sensitive_data),
    # --- Algorithm Complexity: mutually exclusive, highest applicable only ---
    Rule("complexity_llm_genai", "LLM complexity", 20, _is_generative_ai, group="complexity"),
    Rule("complexity_deep_learning", "deep learning complexity", 20, _is_deep_learning,
         group="complexity"),
    Rule("complexity_traditional_ml", "traditional ML complexity", 10, _is_traditional_ml,
         group="complexity"),
    # --- Vendor Dependency: independent add ---
    Rule("vendor_blackbox_external", "black-box external model", 20, _is_external_blackbox_vendor),
]


def _categorize(score: int) -> RiskCategory:
    if score >= HIGH_THRESHOLD:
        return RiskCategory.HIGH
    if score >= MEDIUM_THRESHOLD:
        return RiskCategory.MEDIUM
    return RiskCategory.LOW


def _build_explanation(
    score: int, category: RiskCategory, factor_breakdown: list[FactorContribution]
) -> str:
    if not factor_breakdown:
        return f"Score {score} ({category.value}): no risk factors identified."
    parts = ", ".join(f"{f.reason} (+{f.points})" for f in factor_breakdown)
    return f"Score {score} ({category.value}): {parts}"


def assess(risk_input: RiskInput) -> RiskResult:
    """The single public entry point. Pure. No side effects."""
    matched = [rule for rule in RULES if rule.predicate(risk_input)]

    best_per_group: dict[str, Rule] = {}
    winning_keys: set[str] = set()
    for rule in matched:
        if rule.group is None:
            winning_keys.add(rule.key)
            continue
        current = best_per_group.get(rule.group)
        if current is None or rule.points > current.points:
            best_per_group[rule.group] = rule
    winning_keys.update(rule.key for rule in best_per_group.values())

    # Iterate RULES (not `matched`) to keep breakdown order stable and
    # deterministic regardless of dict/set iteration order.
    fired = [rule for rule in RULES if rule.key in winning_keys]

    score = sum(rule.points for rule in fired)
    factor_breakdown = [
        FactorContribution(key=rule.key, reason=rule.reason, points=rule.points) for rule in fired
    ]
    assert sum(f.points for f in factor_breakdown) == score  # invariant, see module docstring

    category = _categorize(score)
    explanation = _build_explanation(score, category, factor_breakdown)

    return RiskResult(
        score=score, category=category, factor_breakdown=factor_breakdown, explanation=explanation
    )
