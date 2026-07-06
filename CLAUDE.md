# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Python service (root of repo, managed with `uv`):

```bash
uv sync                    # install/sync deps into .venv
uv run pytest              # run full test suite
uv run pytest tests/test_sqlite_template_store.py -k test_categorize_is_idempotent  # single test
uv run uvicorn logtriage.main:app --reload --port 8000  # run the API locally
```

Dashboard (`dashboard/`, Next.js):

```bash
cd dashboard
npm install
cp .env.local.example .env.local   # set LOGTRIAGE_API_URL if API isn't on localhost:8000
npm run dev                        # requires the API already running
npm run build                      # production build
npx tsc --noEmit                   # typecheck
npx eslint .                       # lint
```

Helm chart (`charts/log-triage/`):

```bash
helm lint charts/log-triage
helm template test charts/log-triage -f charts/log-triage/values-production.yaml.example
```

Local end-to-end stack:

```bash
docker compose up      # app + Fluent Bit (generates + ships logs) + Prometheus
```

## Architecture

This is a self-hostable log triage service: logs come in via Fluent Bit,
Drain3 clusters them into templates, new templates wait for a human (or
future AI agent) to assign a severity/mute pair, and every log is then
counted into Prometheus buckets. See the root `README.md` for the full
conceptual model — the notes below are what you need to navigate the code.

**Ports & adapters.** `src/logtriage/ports/` defines four ABCs
(`Clusterer`, `TemplateStore`, `ObjectStore`, `MetricsSink`); concrete
implementations live in `src/logtriage/adapters/`. `factory.py` is the only
place that wires config → concrete adapter — nothing in `worker/` or `api/`
imports drain3, sqlite3, boto3, or prometheus_client directly (they only see
the ports). When adding a new backend (e.g. a new object-store provider),
add the adapter + a branch in `factory.build_object_store`, not a special
case in the pipeline.

**Single writer thread.** Drain3 is not thread-safe for concurrent training,
so exactly one background thread (`worker/pipeline.py: PipelineWorker`) ever
calls `Clusterer.add_log_message()`. It owns Drain3 state, the SQLite
connection, and the archive buffer. `POST /ingest` (async, in `api/ingest.py`)
only ever does `queue.put_nowait()` — never touches Drain3/SQLite/object
storage directly. Keep it that way; don't add synchronous clustering calls
to the request path.

**Category state lives in SQLite, not Drain3.** Drain3's `cluster_id` is
the join key. `change_type == "cluster_created"` → new `pending` row.
`cluster_template_changed` → update the stored template string on the
*existing* row, do not reopen it for review. Everything else is a match-count
bump. This branching logic is in `worker/pipeline.py: process_record` — it's
the one function most bugs will hide in, and it's exercised directly (no
thread/queue involved) in `tests/test_change_type_handling.py`.

**Metric label resolution**: pending cluster → `severity="uncategorized"`,
`muted=false`, regardless of what's eventually assigned. Categorized cluster
→ whatever's stored on its row. Never put `cluster_id` or template strings in
a Prometheus label (cardinality) — per-template data lives in SQLite, exposed
via `/api/templates`.

**Object storage is opt-in**, defaulting to `object_store_backend: "none"`
(a no-op `NullObjectStore`). It exists to preserve a per-line, categorized
archive (original fields + `cluster_id` + resolved `severity`/`muted`) that
SQLite doesn't retain — SQLite only tracks aggregate counts and a handful of
capped sample lines per cluster. Don't assume every deployment has archival
running; metrics/clustering work identically with it off.

**Dashboard (`dashboard/`) is a separate Next.js app, not a static page**,
specifically so auth can be added later without changing the FastAPI service.
Browser-side mutations go through `dashboard/src/app/api/[...path]/route.ts`
(a proxy Route Handler to `LOGTRIAGE_API_URL`); Server Components fetch the
API directly server-side for initial page data. If you add a new API call
from a client component, route it through that proxy, not directly to the
API origin — note the proxy re-prepends `api/` to the path since FastAPI's
template endpoints live under `/api/...` themselves (see the comment in that
file if this trips you up again).

**Helm chart is single-replica by design.** The worker-thread/SQLite/Drain3
design is a single-writer architecture; the chart enforces `replicaCount: 1`
and `strategy: Recreate` so a rollout never runs two pods against the same
ReadWriteOnce PVC. Don't add HPA or multi-replica support without first
addressing Drain3/SQLite's single-writer constraint (see `charts/log-triage/README.md`).

## Testing patterns

`tests/fakes.py` provides in-memory fakes for all four ports. Prefer testing
`worker/pipeline.py: process_record` directly against fakes (fast, no
threads) over going through `PipelineWorker`'s queue/thread machinery unless
you're specifically testing the threading/shutdown behavior itself (see
`tests/test_pipeline.py` for the latter). `tests/test_api.py` uses a real
`PrometheusMetricsSink` with an isolated `CollectorRegistry` (not the global
one, and not a fake) because `/metrics` is a real HTTP contract worth
exercising against the actual prometheus_client wiring.
