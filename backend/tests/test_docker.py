"""
Integration tests for the Docker Compose deployment — these test the
DEPLOYMENT, not the features (those are covered by the rest of the suite
against a plain sqlite DB). They build a real image and start real
containers, so they're slow (30-60s) and deliberately NOT part of the
default fast suite — opt in explicitly:

    RUN_DOCKER_TESTS=1 pytest tests/test_docker.py -v

Skipped automatically otherwise, and also skipped if `docker` isn't on PATH.
"""

import os
import shutil
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOCKER_AVAILABLE = shutil.which("docker") is not None
RUN_DOCKER_TESTS = os.environ.get("RUN_DOCKER_TESTS") == "1"

pytestmark = pytest.mark.skipif(
    not (DOCKER_AVAILABLE and RUN_DOCKER_TESTS),
    reason="opt-in: set RUN_DOCKER_TESTS=1 with docker installed to run these",
)


def _compose(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "compose", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=check,
    )


def _wait_for_health(timeout: float = 60.0) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = httpx.get("http://localhost:8000/health", timeout=2.0)
            if response.status_code == 200:
                return
        except httpx.HTTPError as exc:
            last_error = exc
        time.sleep(1)
    raise TimeoutError(f"App did not become healthy within {timeout}s: {last_error}")


@pytest.fixture(scope="module")
def compose_stack() -> Iterator[None]:
    _compose("down", "-v", check=False)  # clean slate, ignore "nothing to remove"
    build = _compose("build")
    assert build.returncode == 0, build.stderr
    up = _compose("up", "-d")
    assert up.returncode == 0, up.stderr
    _wait_for_health()
    yield
    _compose("down", "-v", check=False)


def test_health_returns_ok(compose_stack: None) -> None:
    response = httpx.get("http://localhost:8000/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_models_endpoint_returns_three_seeded_models(compose_stack: None) -> None:
    response = httpx.get("http://localhost:8000/models")
    assert response.status_code == 200
    models = response.json()
    assert len(models) == 3
    assert {m["name"] for m in models} == {
        "Credit Underwriting Scorecard v3", "Fraud Detection Vendor API", "Customer Support Assistant",
    }


def test_seed_gate_decisions_are_correct(compose_stack: None) -> None:
    models = {m["name"]: m["id"] for m in httpx.get("http://localhost:8000/models").json()}
    rows = httpx.get("http://localhost:8000/audit-logs", params={"limit": 500}).json()
    decisions = {
        r["model_id"]: r["guardrail_result"]
        for r in rows if r["action"] == "DEPLOYMENT_GATE_CHECKED"
    }
    assert decisions[models["Credit Underwriting Scorecard v3"]] == "ALLOW"
    assert decisions[models["Fraud Detection Vendor API"]] == "BLOCKED"
    assert decisions[models["Customer Support Assistant"]] == "BLOCKED"


def test_restart_preserves_data_without_crashing(compose_stack: None) -> None:
    """Guards against the exact bug this story found and fixed: a naive
    seed_data.py would raise DuplicateModelError on a restart against a
    persisted volume, aborting the `&&`-chained startup command before
    uvicorn ever starts."""
    restart = _compose("restart", "app")
    assert restart.returncode == 0, restart.stderr
    _wait_for_health()

    response = httpx.get("http://localhost:8000/models")
    assert response.status_code == 200
    assert len(response.json()) == 3
