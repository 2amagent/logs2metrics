import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry

from logtriage.adapters.prometheus_metrics_sink import PrometheusMetricsSink
from logtriage.api import health, ingest, templates
from logtriage.worker.archive_buffer import ArchiveBuffer
from logtriage.worker.pipeline import PipelineWorker
from tests.fakes import FakeClusterer, FakeObjectStore, FakeTemplateStore


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(ingest.router)
    app.include_router(templates.router)
    app.include_router(health.router)

    store = FakeTemplateStore()
    # Real sink here (not a fake): /metrics is a genuine HTTP contract over a
    # prometheus_client registry, so this test exercises that wiring for real.
    # An isolated registry (not the global one) keeps test runs independent.
    registry = CollectorRegistry()
    metrics = PrometheusMetricsSink(registry=registry)
    clusterer = FakeClusterer()
    buffer = ArchiveBuffer(FakeObjectStore(), metrics, flush_size_bytes=10_000_000, flush_interval_seconds=9999)
    worker = PipelineWorker(
        message_field="log", queue_max_size=100, clusterer=clusterer, store=store, metrics=metrics, buffer=buffer
    )
    worker.start()

    app.state.template_store = store
    app.state.metrics = metrics
    app.state.metrics_registry = registry
    app.state.worker = worker
    app.state.ready = True

    with TestClient(app) as c:
        yield c

    worker.shutdown()


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200


def test_readyz(client):
    r = client.get("/readyz")
    assert r.status_code == 200


def test_ingest_then_list_pending_then_categorize_then_metrics(client):
    import time

    r = client.post("/ingest", json=[{"log": "disk full on node-1"}])
    assert r.status_code == 202
    assert r.json() == {"accepted": 1}

    deadline = time.monotonic() + 2
    templates_resp = []
    while time.monotonic() < deadline:
        templates_resp = client.get("/api/templates", params={"status": "pending"}).json()
        if templates_resp:
            break
        time.sleep(0.02)

    assert len(templates_resp) == 1
    cluster_id = templates_resp[0]["cluster_id"]

    r = client.post(f"/api/templates/{cluster_id}/categorize", json={"severity": "error", "muted": False})
    assert r.status_code == 200
    assert r.json()["status"] == "categorized"

    r = client.post("/ingest", json=[{"log": "disk full on node-1"}])
    assert r.status_code == 202

    deadline = time.monotonic() + 2
    body = ""
    while time.monotonic() < deadline:
        body = client.get("/metrics").text
        if 'logtriage_logs_total{muted="false",severity="error"} 1.0' in body:
            break
        time.sleep(0.02)

    assert 'logtriage_logs_total{muted="false",severity="error"} 1.0' in body


def test_categorize_unknown_cluster_404(client):
    r = client.post("/api/templates/9999/categorize", json={"severity": "info", "muted": False})
    assert r.status_code == 404


def test_get_unknown_template_404(client):
    r = client.get("/api/templates/9999")
    assert r.status_code == 404
