"""
Seed the database with three demo models spanning the three governance
outcomes an NBFC CRO needs to see: ALLOW (clean), BLOCKED (missing several
mandatory controls), BLOCKED (missing one, lower severity). Run this once
against a fresh DB and the platform demos immediately — no manual
registration needed.

Uses the ORM + the real service layer (create_model / assess_model /
assess_model_controls / check_deployment) — the exact same code path the
API uses — so seeded data is governed by identical rules, not hand-crafted
rows that could drift from what the engines actually compute.

Run from backend/:  python scripts/seed_data.py

NOTE ON EXPECTED NUMBERS: this story's brief quotes approximate risk scores
("~50", "~80", "~45") and finding counts (2 for model 2, 1 for model 3)
that don't match what the real, already-built risk and control engines
compute for these exact payloads — confirmed by literally running this
scenario multiple times earlier in this project (see docs/demo-walkthrough.md).
The real numbers are printed below and used in tests/test_seed.py:
  - Model 1 scores 60 (MEDIUM, not the ~50/HIGH implied), and MEDIUM tier
    only requires 4 controls, not 9 — still an ALLOW, all attestations
    being True satisfies whichever tier it lands in.
  - Model 2 scores 70 (HIGH). Its payload sets FOUR attestations false
    (independent_validation, explainability, drift_monitoring,
    deployment_approval), not two — all four are HIGH-tier-required, so
    all four produce findings, not two.
  - Model 3 scores 45 (MEDIUM) — matches the brief. But its payload sets
    TWO attestations false (independent_validation, drift_monitoring), and
    both are MEDIUM-tier-required, so both produce findings, not one.
"""

import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy.orm import Session  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models.enums import (  # noqa: E402
    BusinessFunction,
    DataClassification,
    DeploymentStage,
    ModelType,
    VendorDependency,
)
from app.schemas.ai_model import AIModelCreate  # noqa: E402
from app.services.ai_model import create_model  # noqa: E402
from app.services.control import assess_model_controls  # noqa: E402
from app.services.gate import check_deployment  # noqa: E402
from app.services.regulatory_seed import seed_regulatory_mappings  # noqa: E402
from app.services.risk import assess_model  # noqa: E402

MODEL_1 = AIModelCreate(
    name="Credit Underwriting Scorecard v3",
    business_function=BusinessFunction.LOAN_UNDERWRITING,
    model_type=ModelType.MACHINE_LEARNING,
    deployment_stage=DeploymentStage.PRODUCTION,
    data_classification=DataClassification.RESTRICTED,
    vendor_dependency=VendorDependency.INTERNAL,
    business_owner="Anuj Sharma",
    risk_owner="Priya Verma",
    technical_owner="Vikram Singh",
    has_documentation=True,
    has_independent_validation=True,
    has_explainability=True,
    has_drift_monitoring=True,
    has_human_override=True,
    has_audit_logging=True,
    has_deployment_approval=True,
)

MODEL_2 = AIModelCreate(
    name="Fraud Detection Vendor API",
    business_function=BusinessFunction.FRAUD_DETECTION,
    model_type=ModelType.THIRD_PARTY_AI_API,
    deployment_stage=DeploymentStage.PRODUCTION,
    data_classification=DataClassification.RESTRICTED,
    vendor_dependency=VendorDependency.EXTERNAL_VENDOR,
    vendor_name="FraudShield Inc",
    business_owner="Ravinder Patel",
    risk_owner="Neha Kapoor",
    technical_owner="Amit Kumar",
    has_documentation=True,
    has_independent_validation=False,
    has_explainability=False,
    has_drift_monitoring=False,
    has_human_override=True,
    has_audit_logging=True,
    has_deployment_approval=False,
)

MODEL_3 = AIModelCreate(
    name="Customer Support Assistant",
    business_function=BusinessFunction.CUSTOMER_SERVICE,
    model_type=ModelType.GENERATIVE_AI,
    deployment_stage=DeploymentStage.TESTING,
    data_classification=DataClassification.INTERNAL,
    vendor_dependency=VendorDependency.EXTERNAL_VENDOR,
    vendor_name="Anthropic",
    llm_provider="Anthropic",
    llm_model_name="Claude 3.5 Sonnet",
    business_owner="Rajesh Menon",
    risk_owner="Divya Iyer",
    technical_owner="Suresh Desai",
    has_documentation=True,
    has_independent_validation=False,
    has_explainability=True,
    has_drift_monitoring=False,
    has_human_override=True,
    has_audit_logging=True,
    has_deployment_approval=False,
)


def _reset_sqlite_file(database_url: str) -> None:
    """Fresh slate. sqlite-only — this script is for local demo setup, not
    a production reset tool. sqlite URL convention: sqlite:///relative/path
    (3 slashes) vs sqlite:////absolute/path (4 slashes, the 4th starts the
    absolute path) — urlparse doesn't cleanly distinguish these, so this is
    plain string handling instead."""
    if not database_url.startswith("sqlite"):
        return
    suffix = database_url.removeprefix("sqlite:///")
    db_path = Path(suffix) if suffix.startswith("/") else (BACKEND_DIR / suffix).resolve()
    db_path.unlink(missing_ok=True)


def _run_migrations() -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR, check=True,
    )


def _seed_model(db: Session, payload: AIModelCreate) -> tuple[str, str]:
    model = create_model(db, payload)
    assess_model(db, model.id)
    assess_model_controls(db, model.id)
    gate_result = check_deployment(db, model.id)
    return model.name, gate_result.decision


def main() -> None:
    settings = get_settings()
    _reset_sqlite_file(settings.database_url)
    _run_migrations()

    db = SessionLocal()
    try:
        seed_regulatory_mappings(db)
        results = [_seed_model(db, payload) for payload in (MODEL_1, MODEL_2, MODEL_3)]
    finally:
        db.close()

    print("✓ Seeded 3 models with full governance state")
    for name, decision in results:
        print(f"  {name} → {decision}")


if __name__ == "__main__":
    main()
