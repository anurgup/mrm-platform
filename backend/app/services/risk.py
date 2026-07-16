"""Adapter between the AI model inventory and the pure risk engine, plus
persistence. This is the ONLY place the engine touches SQLAlchemy — the
engine itself (app/engines/risk.py) stays pure and untouched."""

from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.risk import RiskInput, assess
from app.errors import ModelNotFoundError
from app.models import AIModel, RiskAssessment
from app.services.audit import write_audit


def risk_input_from_model(ai_model: AIModel) -> RiskInput:
    """Plain field mapping — no logic. The engine's rules do the reasoning."""
    return RiskInput(
        business_function=ai_model.business_function,
        model_type=ai_model.model_type,
        data_classification=ai_model.data_classification,
        vendor_dependency=ai_model.vendor_dependency,
    )


def assess_model(db: Session, model_id: int, *, user: str = "risk_analyst") -> RiskAssessment:
    """Run the pure engine and persist the result as a NEW row — assessments
    are additive so a model's risk history is kept, never overwritten."""
    model = db.get(AIModel, model_id)
    if model is None:
        raise ModelNotFoundError(f"No model with id={model_id}")

    result = assess(risk_input_from_model(model))

    assessment = RiskAssessment(
        model_id=model.id,
        risk_score=result.score,
        risk_category=result.category,
        assessment_reason=result.explanation,
        factor_breakdown=[asdict(f) for f in result.factor_breakdown],
    )
    db.add(assessment)
    db.flush()
    write_audit(
        db, "RISK_ASSESSED", user=user, model_id=model.id,
        risk_assessment_result=result.category.value,
    )
    db.commit()
    db.refresh(assessment)
    return assessment


def get_latest_assessment(db: Session, model_id: int) -> RiskAssessment | None:
    stmt = (
        select(RiskAssessment)
        .where(RiskAssessment.model_id == model_id)
        .order_by(RiskAssessment.assessed_at.desc(), RiskAssessment.id.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def get_assessment_history(db: Session, model_id: int) -> list[RiskAssessment]:
    stmt = (
        select(RiskAssessment)
        .where(RiskAssessment.model_id == model_id)
        .order_by(RiskAssessment.assessed_at.desc(), RiskAssessment.id.desc())
    )
    return list(db.execute(stmt).scalars().all())
