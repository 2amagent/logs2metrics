# AGENTS.md

Guidance for AI coding agents working in this repository. See `CLAUDE.md` for
deeper architectural notes (ports/adapters, single-writer threading model,
category resolution logic) — this file covers conventions and commands.

## Repo layout

- `src/logtriage/` — Python service (FastAPI + Drain3 + Prometheus), managed
  with `uv`.
- `dashboard/` — Next.js dashboard, a separate app with its own
  `dashboard/AGENTS.md`/`dashboard/CLAUDE.md` (has Next.js-version-specific
  notes — read it before touching anything under `dashboard/`).
- `charts/log-triage/` — Helm chart for production Kubernetes deployment.
- `docker-compose.yml`, `docker/`, `prometheus/` — local dev stack.
- `tests/` — pytest suite for the Python service, with in-memory fakes for
  every port in `tests/fakes.py`.

## Commands

```bash
uv run pytest                        # Python test suite
uv run uvicorn logtriage.main:app --reload --port 8000   # run the API
docker compose up                    # full local stack (app + Fluent Bit + Prometheus)
helm lint charts/log-triage          # validate the Helm chart

cd dashboard && npm run dev          # dashboard (needs the API running separately)
cd dashboard && npx tsc --noEmit && npx eslint .
```

## Conventions

- Don't import vendor SDKs (`drain3`, `boto3`, `sqlite3`, `prometheus_client`)
  outside `src/logtriage/adapters/` and `src/logtriage/factory.py`. The
  pipeline and API layers only depend on the ABCs in `src/logtriage/ports/`.
- Don't add synchronous Drain3/SQLite/object-store calls to the `/ingest`
  request path — all of that happens on the single background worker thread
  in `worker/pipeline.py`.
- Don't add Prometheus labels with unbounded cardinality (`cluster_id`,
  template strings). Per-template detail belongs in SQLite, surfaced via
  `/api/templates`.
- Don't increase the Helm chart's `replicaCount` or otherwise enable
  multi-replica deployment without first addressing Drain3/SQLite's
  single-writer constraint.
- When the dashboard needs a new API call from a client component, route it
  through `dashboard/src/app/api/[...path]/route.ts`, not directly to the API
  origin, so future auth work has one seam to modify.
