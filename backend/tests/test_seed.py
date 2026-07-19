"""
Tests for scripts/seed_data.py — runs the REAL script as a subprocess
against an isolated temp sqlite file, then verifies the seeded state
directly via the ORM. This exercises the actual CLI entry point, not a
reimplementation of it.

Expected finding counts here are the numbers the real engines produce for
these exact payloads (verified independently multiple times against a live
server — see docs/demo-walkthrough.md), not the story brief's approximate
guesses: Model 2's payload sets four attestations false (all four are
HIGH-tier-required), so it has 4 open findings, not 2. Model 3's payload
sets two attestations false (both MEDIUM-tier-required), so it has 2 open
findings, not 1. Model 1 lands at MEDIUM tier (score 60), not HIGH — still
an ALLOW either way since every attestation is True.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import AIModel, AuditLog, Finding, FindingStatus

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def seed_run(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str]:
    db_path = tmp_path_factory.mktemp("seed") / "mrm.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db_path}"}
    result = subprocess.run(
        [sys.executable, "scripts/seed_data.py"],
        cwd=BACKEND_DIR, env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    return db_path, result.stdout


@pytest.fixture(scope="module")
def seeded_session(seed_run: tuple[Path, str]) -> Session:
    db_path, _ = seed_run
    engine = create_engine(f"sqlite:///{db_path}")
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _model_by_name(session: Session, name: str) -> AIModel:
    return session.execute(select(AIModel).where(AIModel.name == name)).scalar_one()


def test_seed_output_reports_all_three_decisions(seed_run: tuple[Path, str]) -> None:
    _, stdout = seed_run
    assert "Credit Underwriting Scorecard v3 → ALLOW" in stdout
    assert "Fraud Detection Vendor API → BLOCKED" in stdout
    assert "Customer Support Assistant → BLOCKED" in stdout


def test_three_models_in_inventory(seeded_session: Session) -> None:
    models = seeded_session.execute(select(AIModel)).scalars().all()
    assert len(models) == 3
    assert {m.name for m in models} == {
        "Credit Underwriting Scorecard v3", "Fraud Detection Vendor API", "Customer Support Assistant",
    }


def test_model_1_has_zero_findings(seeded_session: Session) -> None:
    model = _model_by_name(seeded_session, "Credit Underwriting Scorecard v3")
    findings = seeded_session.execute(
        select(Finding).where(Finding.model_id == model.id)
    ).scalars().all()
    assert findings == []


def test_model_2_blocked_with_four_findings(seeded_session: Session) -> None:
    model = _model_by_name(seeded_session, "Fraud Detection Vendor API")
    findings = seeded_session.execute(
        select(Finding).where(Finding.model_id == model.id, Finding.status != FindingStatus.CLOSED)
    ).scalars().all()
    assert len(findings) == 4
    assert {f.control_key for f in findings} == {
        "independent_validation", "explainability", "drift_monitoring", "deployment_approval",
    }
    assert all(f.severity == "HIGH" for f in findings)


def test_model_3_blocked_with_two_findings(seeded_session: Session) -> None:
    model = _model_by_name(seeded_session, "Customer Support Assistant")
    findings = seeded_session.execute(
        select(Finding).where(Finding.model_id == model.id, Finding.status != FindingStatus.CLOSED)
    ).scalars().all()
    assert len(findings) == 2
    assert {f.control_key for f in findings} == {"independent_validation", "drift_monitoring"}
    assert all(f.severity == "MEDIUM" for f in findings)


def test_total_open_findings_across_all_models(seeded_session: Session) -> None:
    findings = seeded_session.execute(
        select(Finding).where(Finding.status != FindingStatus.CLOSED)
    ).scalars().all()
    assert len(findings) == 6


def test_audit_trail_has_all_four_action_types_per_model(seeded_session: Session) -> None:
    rows = seeded_session.execute(select(AuditLog)).scalars().all()
    assert len(rows) == 12

    actions_by_model: dict[int | None, set[str]] = {}
    for row in rows:
        actions_by_model.setdefault(row.model_id, set()).add(row.action)

    assert len(actions_by_model) == 3
    for actions in actions_by_model.values():
        assert actions == {
            "MODEL_REGISTERED", "RISK_ASSESSED", "CONTROL_ASSESSED", "DEPLOYMENT_GATE_CHECKED",
        }
