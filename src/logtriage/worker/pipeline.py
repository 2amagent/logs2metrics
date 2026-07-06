import logging
import queue
import threading

from logtriage.ports.clusterer import Clusterer
from logtriage.ports.metrics_sink import MetricsSink
from logtriage.ports.template_store import TemplateStore
from logtriage.worker.archive_buffer import ArchiveBuffer

logger = logging.getLogger(__name__)

_SENTINEL = object()


def process_record(
    record: dict,
    message_field: str,
    clusterer: Clusterer,
    store: TemplateStore,
    metrics: MetricsSink,
    buffer: ArchiveBuffer,
) -> None:
    """Process a single ingest record end to end. Pure function of its dependencies so it's
    directly testable with fakes, independent of the queue/thread machinery."""
    message = record.get(message_field, "")
    result = clusterer.add_log_message(message)
    cluster_id = result["cluster_id"]
    template = result["template_mined"]
    change_type = result["change_type"]

    if change_type == "cluster_created":
        store.create_pending(cluster_id, template, message)
        metrics.inc_new_templates_total()
        metrics.set_templates_pending(store.count_pending())
        metrics.set_templates_total(store.count_total())
    elif change_type == "cluster_template_changed":
        store.update_template(cluster_id, template)
        store.record_match(cluster_id, message)
    else:
        store.record_match(cluster_id, message)

    row = store.get(cluster_id)
    if row is None or row.status == "pending":
        severity, muted = "uncategorized", False
    else:
        severity, muted = row.severity, row.muted

    metrics.inc_logs_total(severity, muted)

    enriched = dict(record)
    enriched["cluster_id"] = cluster_id
    enriched["severity"] = severity
    enriched["muted"] = muted
    buffer.add(enriched)
    buffer.maybe_flush()


class PipelineWorker:
    """Owns the queue, the background thread, and all single-writer state (Drain3, SQLite,
    the archive buffer). /ingest only ever calls .enqueue()."""

    def __init__(
        self,
        message_field: str,
        queue_max_size: int,
        clusterer: Clusterer,
        store: TemplateStore,
        metrics: MetricsSink,
        buffer: ArchiveBuffer,
    ):
        self._message_field = message_field
        self._queue: queue.Queue = queue.Queue(maxsize=queue_max_size)
        self._clusterer = clusterer
        self._store = store
        self._metrics = metrics
        self._buffer = buffer
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="logtriage-worker", daemon=True)
        self._thread.start()

    def enqueue(self, record: dict) -> bool:
        """Returns False if the queue is full (backpressure) — caller should respond 503."""
        try:
            self._queue.put_nowait(record)
        except queue.Full:
            return False
        self._metrics.set_queue_depth(self._queue.qsize())
        return True

    def _run(self) -> None:
        while True:
            item = self._queue.get()
            if item is _SENTINEL:
                break
            try:
                process_record(
                    item, self._message_field, self._clusterer, self._store, self._metrics, self._buffer
                )
            except Exception:
                logger.exception("error processing queued record")
                self._metrics.inc_processing_errors_total()
            finally:
                self._metrics.set_queue_depth(self._queue.qsize())

    def shutdown(self, timeout: float = 10.0) -> None:
        """Best-effort graceful drain: stop accepting new work via sentinel, wait for the
        thread to finish in-flight items, then flush the archive buffer and persist Drain3 state."""
        self._queue.put(_SENTINEL)
        if self._thread is not None:
            self._thread.join(timeout=timeout)
        self._buffer.flush()
        self._clusterer.save_state()
