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
