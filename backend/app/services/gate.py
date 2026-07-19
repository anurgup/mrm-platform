"""The deployment gate: the single point where risk tier, control status,
and open findings converge into one ALLOW/BLOCKED decision with RBI-anchored
reasons. Stateless — no new tables, just evaluation plus an audit record of
the check itself.

DECISION LOGIC (deterministic, in order):
  1. control_assessment.overall_status == "FAIL" -> BLOCKED
  2. any open finding has severity HIGH               -> BLOCKED
  3. otherwise                                        -> ALLOW
When BLOCKED, blocking_findings lists EVERY open finding (not just the HIGH
ones) — a FAIL-triggered block should show every open reason, and a
HIGH-finding-triggered block should show at least those, so showing the
full open set is always the more complete, more honest answer."""

from typing import Literal

from sqlalchemy.orm import Session

from app.errors import AssessmentNotFoundError, ModelNotFoundError
from app.models import AIModel, Severity
from app.schemas.gate import BlockingFinding, DeploymentCheckResult
from app.services.audit import write_audit
from app.services.control import get_control_findings, get_latest_control_assessment
from app.services.risk import get_latest_assessment as get_latest_risk_assessment


def _build_message(decision: str, blocking_findings: list[BlockingFinding]) -> str:
    if decision == "ALLOW":
        return "All controls satisfied. Deployment allowed."

    names = ", ".join((bf.control_key or "unspecified control").replace("_", " ") for bf in blocking_findings)
    regulations = sorted({bf.regulation_name for bf in blocking_findings if bf.regulation_name})
    reg_suffix = f" per {', '.join(regulations)}" if regulations else ""
    severity_label = "HIGH-severity" if any(bf.severity == Severity.HIGH for bf in blocking_findings) else "open"
    count = len(blocking_findings)
    plural = "s" if count != 1 else ""
    return f"BLOCKED: {count} {severity_label} control gap{plural} ({names}){reg_suffix}."


def check_deployment(db: Session, model_id: int, *, user: str = "gate") -> DeploymentCheckResult:
    model = db.get(AIModel, model_id)
    if model is None:
        raise ModelNotFoundError(f"No model with id={model_id}")

    risk_assessment = get_latest_risk_assessment(db, model_id)
    if risk_assessment is None:
        raise AssessmentNotFoundError(
            f"No risk assessment exists yet for model id={model_id}; "
            "can't check the deployment gate without a risk assessment"
        )

    control_assessment = get_latest_control_assessment(db, model_id)
    if control_assessment is None:
        raise AssessmentNotFoundError(
            f"No control assessment exists yet for model id={model_id}; "
            "can't check the deployment gate without a control assessment"
        )

    open_findings = get_control_findings(db, model_id)
    has_open_high = any(f.severity == Severity.HIGH for f in open_findings)
    blocked = control_assessment.overall_status == "FAIL" or has_open_high
    decision: Literal["ALLOW", "BLOCKED"] = "BLOCKED" if blocked else "ALLOW"

    blocking_findings: list[BlockingFinding] = []
    if blocked:
        for finding in open_findings:
            reference = finding.regulatory_reference or {}
            blocking_findings.append(BlockingFinding(
                control_key=finding.control_key,
                title=finding.title,
                severity=finding.severity,
                regulation_name=reference.get("regulation_name"),
                reference_text=reference.get("reference_text"),
            ))

    message = _build_message(decision, blocking_findings)

    audit_row = write_audit(
        db, "DEPLOYMENT_GATE_CHECKED", user=user, model_id=model.id,
        guardrail_result=decision,
        detail={
            "overall_status": control_assessment.overall_status,
            "open_findings_count": len(open_findings),
        },
    )
    db.commit()
    db.refresh(audit_row)

    return DeploymentCheckResult(
        model_id=model.id,
        decision=decision,
        risk_category=risk_assessment.risk_category,
        risk_score=risk_assessment.risk_score,
        controls_required=control_assessment.controls_required,
        controls_passed=control_assessment.controls_passed,
        overall_status=control_assessment.overall_status,
        open_findings_count=len(open_findings),
        blocking_findings=blocking_findings,
        message=message,
        checked_at=audit_row.timestamp,
        audit_log_id=audit_row.id,
    )
