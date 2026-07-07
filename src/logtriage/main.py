import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from logtriage.api import health, ingest, templates
from logtriage.config import Settings
from logtriage.factory import build_clusterer, build_metrics_sink, build_object_store, build_template_store
from logtriage.logging_config import configure_logging
from logtriage.worker.archive_buffer import ArchiveBuffer
from logtriage.worker.pipeline import PipelineWorker

logger = logging.getLogger(__name__)


def _reconcile(store, clusterer) -> None:
    """Any Drain3 cluster with no metadata row gets a pending row (covers DB/Drain3 state drift)."""
    known = store.known_cluster_ids()
    for cluster_id in clusterer.known_cluster_ids():
        if cluster_id not in known:
            store.create_pending(cluster_id, template="", sample_line="")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_yaml(os.environ.get("LOGTRIAGE_CONFIG_PATH", "config.yaml"))
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        template_store = build_template_store(settings)
        object_store = build_object_store(settings)
        metrics = build_metrics_sink(settings)
        clusterer = build_clusterer(settings)

        _reconcile(template_store, clusterer)

        buffer = ArchiveBuffer(
            object_store=object_store,
            metrics=metrics,
            flush_size_bytes=settings.flush_size_bytes,
            flush_interval_seconds=settings.flush_interval_seconds,
        )
        worker = PipelineWorker(
            message_field=settings.message_field,
            queue_max_size=settings.queue_max_size,
            clusterer=clusterer,
            store=template_store,
            metrics=metrics,
            buffer=buffer,
        )
        worker.start()

        app.state.settings = settings
        app.state.template_store = template_store
        app.state.metrics = metrics
        app.state.worker = worker
        app.state.ready = True

        yield

        app.state.ready = False
        worker.shutdown()

    app = FastAPI(title="log-triage", lifespan=lifespan)
    app.include_router(ingest.router)
    app.include_router(templates.router)
    app.include_router(health.router)
    return app


app = create_app()
