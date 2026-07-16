from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models import (
    AIAsset,
    AIModel,
    AuditLog,
    BusinessFunction,
    ControlAssessment,
    DataClassification,
    Finding,
    GuardrailAction,
    GuardrailPolicy,
    GuardrailStage,
    GuidanceType,
    LLMConfiguration,
    ModelType,
    RegulatoryMapping,
    RemediationAction,
    Report,
    ReportType,
    RiskAssessment,
    RiskCategory,
    Severity,
    VendorDependency,
)

BACKEND_DIR = Path(__file__).resolve().parent.parent

EXPECTED_TABLES = {
    "ai_models", "ai_assets", "risk_assessments", "control_assessments",
    "regulatory_mapping", "findings", "remediation_actions",
    "guardrail_policies", "audit_logs", "llm_configurations", "reports",
}


def _alembic_config(db_url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def _make_session(tmp_path: Path, name: str) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path / name}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _make_ai_model(name: str) -> AIModel:
    return AIModel(
        name=name,
        business_function=BusinessFunction.LOAN_UNDERWRITING,
        model_type=ModelType.MACHINE_LEARNING,
        business_owner="B. Owner",
        risk_owner="R. Owner",
        technical_owner="T. Owner",
        data_classification=DataClassification.CONFIDENTIAL,
        vendor_dependency=VendorDependency.INTERNAL,
    )


def test_migration_round_trip(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'roundtrip.db'}"
    cfg = _alembic_config(db_url)

    command.upgrade(cfg, "head")
    engine = create_engine(db_url)
    tables = set(inspect(engine).get_table_names())
    engine.dispose()
    assert EXPECTED_TABLES <= tables

    command.downgrade(cfg, "base")
    engine = create_engine(db_url)
    remaining = set(inspect(engine).get_table_names()) - {"alembic_version"}
    engine.dispose()
    assert remaining == set()


def test_one_row_per_table_smoke(tmp_path: Path) -> None:
    session = _make_session(tmp_path, "smoke.db")
    try:
        model = _make_ai_model("Smoke Test Model")
        session.add(model)
        session.flush()

        finding = Finding(
            model_id=model.id,
            title="Missing independent validation",
            severity=Severity.HIGH,
            risk_description="No independent validation on record.",
            remediation="Commission independent validation.",
        )
        audit = AuditLog(action="MODEL_CREATED")
        session.add_all([
            AIAsset(name="shadow-tool", source="network-scan", environment="production",
                    linked_model_id=model.id),
            RiskAssessment(model_id=model.id, risk_score=85, risk_category=RiskCategory.HIGH,
                            assessment_reason="High risk due to missing controls.",
                            factor_breakdown={"validation": 0}),
            ControlAssessment(model_id=model.id, risk_category=RiskCategory.HIGH,
                               controls_required=7, controls_passed=4, overall_status="FAIL",
                               detail={"missing": ["explainability"]}),
            RegulatoryMapping(control_key="AUDIT_LOGGING", regulation_name="RBI IT Governance MD",
                               reference_text="Regulated entities must maintain audit logging.",
                               guidance_type=GuidanceType.BINDING),
            finding,
            GuardrailPolicy(name="pii-input-mask", stage=GuardrailStage.INPUT, detector="GLINER",
                             action=GuardrailAction.MASK),
            LLMConfiguration(provider="openai", model="gpt-4o", api_credential_ref="OPENAI_API_KEY"),
            audit,
        ])
        session.flush()

        session.add(RemediationAction(finding_id=finding.id, action="Commission validation",
                                       owner="Risk Team"))
        session.add(Report(model_id=model.id, report_type=ReportType.PDF,
                            file_path="/reports/smoke.pdf", generated_by="system",
                            audit_log_id=audit.id))
        session.flush()

        for table in Base.metadata.tables:
            count = session.execute(
                Base.metadata.tables[table].select()
            ).all()
            assert len(count) == 1, f"expected exactly one row in {table!r} pre-rollback"
    finally:
        session.rollback()
        session.close()

    verify = sessionmaker(bind=session.get_bind())()
    try:
        for table in Base.metadata.tables:
            rows = verify.execute(Base.metadata.tables[table].select()).all()
            assert rows == [], f"expected {table!r} empty after rollback"
    finally:
        verify.close()


def test_ai_model_name_uniqueness(tmp_path: Path) -> None:
    session = _make_session(tmp_path, "uniqueness.db")
    try:
        session.add(_make_ai_model("Duplicate Name"))
        session.commit()

        session.add(_make_ai_model("Duplicate Name"))
        with pytest.raises(IntegrityError):
            session.commit()
    finally:
        session.rollback()
        session.close()
