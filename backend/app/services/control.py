"""Adapter between the AI model inventory + risk assessment and the pure
control engine, plus persistence and findings generation. This is the ONLY
place the engine touches SQLAlchemy — the engine itself
(app/engines/control.py) stays pure and untouched."""

from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.control import ControlInput, FindingDraft, RegulatoryReference, Resolver, evaluate
from app.errors import AssessmentNotFoundError, FindingNotFoundError, ModelNotFoundError
from app.models import AIModel, ControlAssessment, Finding, FindingStatus, RiskAssessment
from app.services.audit import write_audit
from app.services.regulatory import resolve_reference
from app.services.risk import get_latest_assessment as get_latest_risk_assessment


def control_input_from_model(ai_model: AIModel, risk_assessment: RiskAssessment) -> ControlInput:
    """Plain field mapping — no logic. The engine's rules do the reasoning."""
    return ControlInput(
        risk_category=risk_assessment.risk_category,
        has_documentation=ai_model.has_documentation,
        has_independent_validation=ai_model.has_independent_validation,
        has_explainability=ai_model.has_explainability,
        has_drift_monitoring=ai_model.has_drift_monitoring,
        has_human_override=ai_model.has_human_override,
        has_audit_logging=ai_model.has_audit_logging,
        has_deployment_approval=ai_model.has_deployment_approval,
        has_model_owner=bool(ai_model.business_owner and ai_model.business_owner.strip()),
        has_risk_owner=bool(ai_model.risk_owner and ai_model.risk_owner.strip()),
    )


def _make_resolver(db: Session) -> Resolver:
    """resolve_reference() returns a TypedDict, which mypy won't accept as
    structurally interchangeable with the engine's plain dict[str, str | None]
    Resolver signature — this wrapper makes that conversion explicit."""

    def resolve(control_key: str) -> RegulatoryReference | None:
        result = resolve_reference(db, control_key)
        if result is None:
            return None
        return {
            "regulation_name": result["regulation_name"],
            "reference_text": result["reference_text"],
            "guidance_type": result["guidance_type"],
            "effective_note": result["effective_note"],
        }

    return resolve


def _get_or_create_finding(db: Session, model_id: int, draft: FindingDraft) -> Finding:
    """Idempotency via (model_id, control_key): if an OPEN finding for this
    control already exists, it's already tracking the gap — return it as-is
    rather than creating a duplicate. Otherwise create a new one (a control
    that regressed after its finding was closed gets a fresh finding)."""
    existing = db.execute(
        select(Finding).where(
            Finding.model_id == model_id,
            Finding.control_key == draft.control_key,
            Finding.status == FindingStatus.OPEN,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    finding = Finding(
        model_id=model_id,
        title=draft.title,
        severity=draft.severity,
        risk_description=draft.risk_description,
        remediation=draft.remediation,
        regulatory_reference=draft.regulatory_reference,
        control_key=draft.control_key,
        status=FindingStatus.OPEN,
    )
    db.add(finding)
    return finding


def assess_model_controls(
    db: Session, model_id: int, *, user: str = "governance_analyst"
) -> tuple[ControlAssessment, list[Finding]]:
    model = db.get(AIModel, model_id)
    if model is None:
        raise ModelNotFoundError(f"No model with id={model_id}")

    risk_assessment = get_latest_risk_assessment(db, model_id)
    if risk_assessment is None:
        raise AssessmentNotFoundError(
            f"No risk assessment exists yet for model id={model_id}; "
            "assess risk before assessing controls"
        )

    control_input = control_input_from_model(model, risk_assessment)
    result = evaluate(control_input, _make_resolver(db))

    assessment = ControlAssessment(
        model_id=model.id,
        risk_category=result.risk_category,
        controls_required=result.controls_required,
        controls_passed=result.controls_passed,
        overall_status=result.overall_status,
        detail={
            "passed_controls": result.passed_controls,
            "finding_drafts": [asdict(d) for d in result.finding_drafts],
        },
    )
    db.add(assessment)
    db.flush()

    findings = [_get_or_create_finding(db, model.id, draft) for draft in result.finding_drafts]
    db.flush()

    write_audit(
        db, "CONTROL_ASSESSED", user=user, model_id=model.id,
        risk_assessment_result=result.overall_status,
    )
    db.commit()
    db.refresh(assessment)
    for finding in findings:
        db.refresh(finding)
    return assessment, findings


def get_latest_control_assessment(db: Session, model_id: int) -> ControlAssessment | None:
    stmt = (
        select(ControlAssessment)
        .where(ControlAssessment.model_id == model_id)
        .order_by(ControlAssessment.assessed_at.desc(), ControlAssessment.id.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def get_control_findings(db: Session, model_id: int) -> list[Finding]:
    """All open findings for this model (status != CLOSED)."""
    stmt = (
        select(Finding)
        .where(Finding.model_id == model_id, Finding.status != FindingStatus.CLOSED)
        .order_by(Finding.id.desc())
    )
    return list(db.execute(stmt).scalars().all())


def update_finding_status(
    db: Session, finding_id: int, new_status: FindingStatus, *, user: str = "governance_analyst"
) -> Finding:
    finding = db.get(Finding, finding_id)
    if finding is None:
        raise FindingNotFoundError(f"No finding with id={finding_id}")

    finding.status = new_status
    db.flush()
    write_audit(
        db, "FINDING_STATUS_UPDATED", user=user, model_id=finding.model_id,
        detail={"finding_id": finding.id, "status": new_status.value},
    )
    db.commit()
    db.refresh(finding)
    return finding
