"""
Deterministic governance control engine.

PURITY CONTRACT: evaluate() is a pure function — no database access, no I/O,
no randomness, no clock. It never resolves a regulatory reference itself;
instead it accepts an injected `resolve(control_key) -> dict | None` callable,
so the engine has no idea whether that reference came from a database, a
fixture, or thin air. The service layer (P-1.5) will pass in P-1.3's
resolve_reference() bound to a real session; tests pass a fake dict lookup.

Tier checklists (TIER_CHECKLISTS below) and the control->attestation mapping
(CONTROL_ATTESTATION_CHECKS) are DATA, not conditionals — same discipline as
the risk engine (app/engines/risk.py), for the same reason: it's what makes
"which controls are missing" fall out for free instead of being scattered
across if-statements.

CONTROL_KEY CONTRACT: these nine keys are the platform's canonical
vocabulary — they MUST exactly match app/services/regulatory_seed.py's
seeded control_keys wherever a mapping exists:
    documentation, independent_validation, explainability, drift_monitoring,
    human_override, audit_logging
Three keys used here have NO regulatory_mapping row on purpose:
    model_owner, risk_owner  — governance hygiene, not a specific RBI reference
    deployment_approval      — an internal process control, not itself an
                                RBI-mapped item
resolve() returning None for these is the expected, handled case, not an
error — see _build_finding_draft().

SEVERITY RULE: severity tracks the model's risk tier directly — a missing
control on a HIGH-tier model is a HIGH severity finding, MEDIUM on MEDIUM,
LOW on LOW. This is deliberately simple: the tier already encodes how much
scrutiny the model warrants, so the engine doesn't grade individual missing
controls differently within a tier.
"""

from collections.abc import Callable
from dataclasses import dataclass

from app.models.enums import RiskCategory, Severity

RegulatoryReference = dict[str, str | None]
Resolver = Callable[[str], RegulatoryReference | None]


@dataclass(frozen=True)
class ControlInput:
    """The small typed input the engine needs — not an AIModel ORM object.
    The service layer derives has_model_owner/has_risk_owner from whether
    AIModel.business_owner/risk_owner are non-empty strings."""

    risk_category: RiskCategory
    has_documentation: bool
    has_independent_validation: bool
    has_explainability: bool
    has_drift_monitoring: bool
    has_human_override: bool
    has_audit_logging: bool
    has_deployment_approval: bool
    has_model_owner: bool
    has_risk_owner: bool


@dataclass(frozen=True)
class FindingDraft:
    control_key: str
    title: str
    severity: Severity
    risk_description: str
    remediation: str
    regulatory_reference: RegulatoryReference | None


@dataclass(frozen=True)
class ControlResult:
    risk_category: RiskCategory
    controls_required: int
    controls_passed: int
    overall_status: str
    passed_controls: list[str]
    finding_drafts: list[FindingDraft]


TIER_CHECKLISTS: dict[RiskCategory, list[str]] = {
    RiskCategory.HIGH: [
        "model_owner", "risk_owner", "documentation", "independent_validation",
        "explainability", "drift_monitoring", "human_override", "audit_logging",
        "deployment_approval",
    ],
    RiskCategory.MEDIUM: [
        "model_owner", "documentation", "independent_validation", "drift_monitoring",
    ],
    RiskCategory.LOW: [
        "model_owner", "documentation",
    ],
}

CONTROL_ATTESTATION_CHECKS: dict[str, Callable[[ControlInput], bool]] = {
    "model_owner": lambda x: x.has_model_owner,
    "risk_owner": lambda x: x.has_risk_owner,
    "documentation": lambda x: x.has_documentation,
    "independent_validation": lambda x: x.has_independent_validation,
    "explainability": lambda x: x.has_explainability,
    "drift_monitoring": lambda x: x.has_drift_monitoring,
    "human_override": lambda x: x.has_human_override,
    "audit_logging": lambda x: x.has_audit_logging,
    "deployment_approval": lambda x: x.has_deployment_approval,
}

# control_key -> (title, description, remediation)
CONTROL_FINDING_TEXT: dict[str, tuple[str, str, str]] = {
    "model_owner": (
        "No accountable model owner assigned",
        "This model has no designated business owner on record, leaving "
        "accountability for its behaviour and outcomes unclear.",
        "Assign an accountable business owner for this model and record it "
        "in the inventory.",
    ),
    "risk_owner": (
        "No accountable risk owner assigned",
        "This model has no designated risk owner on record, leaving "
        "accountability for its risk oversight unclear.",
        "Assign an accountable risk owner for this model and record it in "
        "the inventory.",
    ),
    "documentation": (
        "Model documentation not completed",
        "This model lacks documentation of its systems, controls, and "
        "decisioning logic.",
        "Complete and record model documentation sufficient for "
        "supervisory review.",
    ),
    "independent_validation": (
        "Independent validation not completed",
        "This model has not undergone independent validation.",
        "Complete independent validation and record approval before "
        "continued production use.",
    ),
    "explainability": (
        "Explainability not available",
        "This model lacks explainability mechanisms for its decisions.",
        "Implement and document explainability mechanisms for this "
        "model's decisions.",
    ),
    "drift_monitoring": (
        "Drift monitoring not enabled",
        "This model is not being monitored for behavioural or "
        "performance drift.",
        "Enable ongoing drift monitoring for this model.",
    ),
    "human_override": (
        "Human override not available",
        "This model lacks a human override mechanism for its decisions.",
        "Implement a human override / escalation path for this model's "
        "decisions.",
    ),
    "audit_logging": (
        "Audit logging not enabled",
        "This model does not maintain audit logging for its decisioning "
        "process.",
        "Enable audit logging and traceability for this model's critical "
        "decisioning.",
    ),
    "deployment_approval": (
        "Deployment approval not recorded",
        "This model's production deployment has not been formally approved.",
        "Obtain and record formal deployment approval for this model.",
    ),
}

_SEVERITY_BY_RISK_TIER: dict[RiskCategory, Severity] = {
    RiskCategory.HIGH: Severity.HIGH,
    RiskCategory.MEDIUM: Severity.MEDIUM,
    RiskCategory.LOW: Severity.LOW,
}


def _build_finding_draft(
    control_key: str, control_input: ControlInput, resolve: Resolver
) -> FindingDraft:
    title, description, remediation = CONTROL_FINDING_TEXT[control_key]
    risk_description = (
        f"{description} Given this model's {control_input.risk_category.value} "
        f"risk tier, this control is mandatory."
    )
    return FindingDraft(
        control_key=control_key,
        title=title,
        severity=_SEVERITY_BY_RISK_TIER[control_input.risk_category],
        risk_description=risk_description,
        remediation=remediation,
        regulatory_reference=resolve(control_key),
    )


def evaluate(control_input: ControlInput, resolve: Resolver) -> ControlResult:
    """The single public entry point. Pure — resolve() is the only place
    anything outside this function's arguments gets consulted, and it's
    injected by the caller."""
    required = TIER_CHECKLISTS[control_input.risk_category]

    passed_controls: list[str] = []
    finding_drafts: list[FindingDraft] = []
    for control_key in required:
        if CONTROL_ATTESTATION_CHECKS[control_key](control_input):
            passed_controls.append(control_key)
        else:
            finding_drafts.append(_build_finding_draft(control_key, control_input, resolve))

    return ControlResult(
        risk_category=control_input.risk_category,
        controls_required=len(required),
        controls_passed=len(passed_controls),
        overall_status="PASS" if not finding_drafts else "FAIL",
        passed_controls=passed_controls,
        finding_drafts=finding_drafts,
    )
