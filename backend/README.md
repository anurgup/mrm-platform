# MRM Platform

A second-line-of-defense AI governance and model risk management platform for
Indian NBFCs — inventorying AI/ML models, running guardrails against their
inputs and outputs, and tracking risk classification, validation, and
regulatory compliance across an institution's model estate.

## Run locally

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

```bash
curl localhost:8000/health
```

## Run with Docker Compose

Runs the full platform (FastAPI app + PostgreSQL) pre-seeded with 3 demo
models. No local Python setup needed — just Docker.

```bash
docker compose up -d
curl localhost:8000/models
```

Or with `make` (targets: `up`, `down`, `down-volumes`, `logs`, `build`,
`restart`, `shell`, `test`, `seed`):

```bash
make up
make logs
```

Data persists across restarts in a named volume (`mrm_postgres_data`). To
reset to a fresh, freshly-seeded database:

```bash
docker compose down -v
docker compose up -d
```

Run the Docker integration tests (builds a real image, starts real
containers — slower than the rest of the suite, so opt-in):

```bash
RUN_DOCKER_TESTS=1 pytest tests/test_docker.py -v
```
