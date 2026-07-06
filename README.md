# log-triage

Self-hostable log triage service: ingests logs via Fluent Bit, clusters them into
templates with Drain3, surfaces new templates for human categorization, and
counts every incoming log into severity/mute buckets exposed as Prometheus
metrics — with optional archival of every log to object storage.

The system is read-only with respect to the logs and the systems that produce
them — it observes, categorizes, counts, and archives. It never writes back to
source systems.

## Architecture

Ports & adapters (hexagonal). The pipeline core imports no vendor SDKs directly;
adapters are selected by config via `src/logtriage/factory.py`.

- **`Clusterer`** (`ports/clusterer.py`) — wraps Drain3. Adapter:
  `adapters/drain3_clusterer.py`. Drain3 is an online clusterer, not a trainable
  classifier — it creates a cluster the first time it sees a new log pattern.
  There is no supervised training step.
- **`TemplateStore`** (`ports/template_store.py`) — CRUD for template metadata
  (cluster_id, template string, severity, muted, status, counts, samples).
  Adapter: `adapters/sqlite_template_store.py` (raw `sqlite3`, single writer).
- **`ObjectStore`** (`ports/object_store.py`) — `put_object(key, data)`. Adapters:
  `object_store_local.py` (dev), `object_store_s3.py` (boto3, works against
  MinIO via `endpoint_url`), `object_store_azure.py` (stub — ships in Phase 2).
- **`MetricsSink`** (`ports/metrics_sink.py`) — thin wrapper over
  `prometheus_client`. Adapter: `adapters/prometheus_metrics_sink.py`.

Category metadata (severity + muted) lives in our own SQLite store, keyed on
Drain3's stable `cluster_id`. Drain3 never knows about categories.

**Single background worker.** Drain3 is not thread-safe for concurrent training,
so all clustering calls happen on one dedicated worker thread
(`worker/pipeline.py`) consuming a `queue.Queue`. `POST /ingest` only enqueues
and returns immediately — it never touches Drain3, SQLite, or the object store.

**Template states.** `pending` (new, awaiting categorization) or `categorized`
(has severity + mute). Logs matching a `pending` cluster count as
`uncategorized` in metrics until someone reviews it via the categorize endpoint.

## Config

Copy `config.example.yaml` to `config.yaml` (or set `LOGTRIAGE_*` env vars —
env overrides file values; nested fields use `__`, e.g.
`LOGTRIAGE_S3__ACCESS_KEY_ID`). The config file path itself is controlled by
`LOGTRIAGE_CONFIG_PATH` (defaults to `./config.yaml`).

Drain3 masking and clustering tuning (`sim_th`, `depth`, `max_children`,
`max_clusters`) live in `drain3.ini`, editable independently of `config.yaml`.

## API

- `POST /ingest` — batch of records (JSON array or NDJSON body) from Fluent
  Bit's `http` output. Enqueues; returns 202 immediately.
- `GET /api/templates?status=&severity=&muted=` — list templates with counts,
  sample lines, timestamps.
- `GET /api/templates/{cluster_id}` — full detail incl. sample lines.
- `POST /api/templates/{cluster_id}/categorize` — body
  `{"severity": "error|warning|info", "muted": bool, "actor": "optional"}`.
  Idempotent; re-categorization allowed. This is the endpoint a future AI agent
  will call.
- `GET /metrics` — Prometheus exposition format.
- `GET /healthz`, `GET /readyz` — readiness flips true only after Drain3 state
  and the DB are loaded and the worker thread has started.

## Metrics

`logtriage_logs_total{severity, muted}` is the headline counter —
`severity ∈ {error, warning, info, uncategorized}`, `muted ∈ {true, false}`.
Muted logs are counted, not dropped; muting is for alert filtering, not data
loss. `cluster_id` and template strings are never used as Prometheus labels
(cardinality) — per-template counts live in SQLite via the `/api/templates`
endpoints.

Also exposed: `logtriage_ingested_total`, `logtriage_new_templates_total`,
`logtriage_templates_pending`, `logtriage_templates_total`,
`logtriage_queue_depth`, `logtriage_processing_errors_total`,
`logtriage_storage_flush_total`, `logtriage_storage_bytes_total`,
`logtriage_storage_errors_total`.

## Object storage archival (optional)

`object_store_backend` defaults to `none` — the service still clusters,
counts, and exposes metrics with archival fully disabled. Enable `local`,
`s3`, or (once implemented) `azure` if you want it.

Why you'd want it: most log transporters (Fluent Bit, Vector, etc.) can
already ship raw logs to a bucket on their own, but that only ever captures
the log as it looked at the source. This service's archive is different — it
captures the *enriched* record (original fields + `cluster_id` + resolved
`severity` + `muted`), which is the only place in the system that keeps a
permanent, per-line record of what a log was categorized as. SQLite only
tracks aggregate/template-level state (a handful of capped sample lines per
cluster, not a full history), so without this archive there's no way to later
answer "show me every raw line that was bucketed as `error` on a given day,"
build an audit trail for why an alert was muted, or assemble a labeled dataset
for a future AI categorization agent. If none of that matters for your
deployment, leaving it off is a reasonable default.

When enabled: enriched records are buffered in memory and flushed as gzipped
NDJSON when a size or time threshold trips (`flush_size_bytes` /
`flush_interval_seconds`). Key layout:
`logs/year=YYYY/month=MM/day=DD/hour=HH/<uuid>.ndjson.gz` for cheap time-range
scans. Storage failures are retried, then surfaced as
`logtriage_storage_errors_total` — they never block or drop ingest.

## Fluent Bit wiring

See `docker/fluentbit/fluent-bit.conf`. A `tail` input reads a log file and
emits records with the raw line under the `log` key by default — no parser
filter needed, since that's exactly the field `/ingest` reads
(`message_field`, default `"log"`). The `http` output uses `Format json`,
which Fluent Bit sends as a single JSON array per flush — matching what
`/ingest` expects.

## Categorization workflow

1. New log patterns appear via `GET /api/templates?status=pending`, each with
   sample raw lines and a match count.
2. A human (or, later, an AI agent) reviews a template's samples and calls
   `POST /api/templates/{cluster_id}/categorize` with a severity and mute flag.
3. All *subsequent* matches of that cluster count into the categorized bucket
   in `logtriage_logs_total`. Already-buffered/archived records are not
   retroactively changed — the archive is an append-only log of what was known
   at ingest time.

## Dashboard (Phase 1)

`dashboard/` is a Next.js app that gives a human a "pending review" queue and
a "categorized" list, both backed directly by the API above — no business
logic of its own. See [`dashboard/README.md`](dashboard/README.md) for setup
and why it's a full Next.js app (auth seam) rather than a static page. Not yet
wired into docker-compose or the Helm chart; run it standalone against a
reachable API for now.

## Local development (docker-compose)

```
docker compose up
```

Brings up the app, Fluent Bit (tailing a log file continuously appended to by
a small Python generator sidecar), and Prometheus (scraping `/metrics`).
Archival is off by default (`object_store_backend: none`) — within seconds you
should see:

- `curl localhost:8000/healthz` / `/readyz` → 200
- `curl "localhost:8000/api/templates?status=pending"` → new templates as
  Fluent Bit forwards generated log lines
- Categorize one via `POST /api/templates/{cluster_id}/categorize`
- `curl localhost:8000/metrics | grep logtriage_logs_total` → bucket shifts
  from `uncategorized` to the categorized severity
- Prometheus UI at `localhost:9090` — target `app:8000` should be up

To also exercise the S3 archival adapter locally, uncomment the `minio` and
`createbuckets` services in `docker-compose.yml` and the `LOGTRIAGE_S3__*` env
vars on `app` (see the comments there) — then MinIO's console at
`localhost:9001` (minioadmin/minioadmin) will show gzipped NDJSON objects
under the `logtriage` bucket.

## Production deployment (Kubernetes / Helm)

See [`charts/log-triage/README.md`](charts/log-triage/README.md) for the full
Helm chart, installation steps, and upgrade/uninstall notes. Summary: a
single-replica Deployment (the app's single-writer Drain3/SQLite design caps
this at one replica for now) backed by a PVC, optional S3-compatible object
storage via `values.yaml` (off by default), and an optional ServiceMonitor for
the Prometheus Operator (also off by default, since not every cluster runs it).

## Tests

```
uv run pytest
```

Uses in-memory fakes (`tests/fakes.py`) for each port, plus a real-sqlite3
adapter test and a real-Prometheus-registry API test. Covers Drain3
`change_type` branching (`cluster_created` / `cluster_template_changed` /
`none`), metric label resolution (pending → uncategorized, categorized →
stored severity/muted), the worker thread's queue/shutdown behavior, and the
full HTTP API surface.

## License

Apache-2.0 — see [LICENSE](LICENSE).
