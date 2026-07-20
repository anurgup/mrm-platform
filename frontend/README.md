# MRM Platform — Frontend

A three-page product demo (model list, model detail, governance findings) for
the MRM Platform backend — built to show an NBFC a working product, not a
bare API.

## Run locally

Requires the backend running at `http://localhost:8000` (see
`../backend/README.md`, or `docker compose up -d` from the repo root).

```bash
npm install
npm run dev
```

Runs on `http://localhost:5173`. The backend's CORS config already allows
this origin by default (`cors_origins` in `app/config.py`).

To point at a different backend URL, set `VITE_API_URL`:

```bash
VITE_API_URL=http://localhost:9000 npm run dev
```

## Build

```bash
npm run build
```

Produces `dist/`, a static bundle — serve with nginx or any static host.

## Pages

- `/` — all models, with risk, controls, and gate decision at a glance
- `/models/:id` — full governance detail for one model: risk factors,
  control checklist, deployment gate banner, open findings (with RBI
  regulation citations), and recent audit trail
