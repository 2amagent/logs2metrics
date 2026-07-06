import gzip
import json
import logging
import time
import uuid
from datetime import datetime, timezone

from logtriage.ports.metrics_sink import MetricsSink
from logtriage.ports.object_store import ObjectStore

logger = logging.getLogger(__name__)


class ArchiveBuffer:
    """Accumulates enriched records, flushing as gzipped NDJSON to the object store
    when a size or time threshold trips. Never raises into the worker loop."""

    def __init__(
        self,
        object_store: ObjectStore,
        metrics: MetricsSink,
        flush_size_bytes: int,
        flush_interval_seconds: float,
        max_retries: int = 3,
    ):
        self._object_store = object_store
        self._metrics = metrics
        self._flush_size_bytes = flush_size_bytes
        self._flush_interval_seconds = flush_interval_seconds
        self._max_retries = max_retries
        self._lines: list[bytes] = []
        self._size_bytes = 0
        self._last_flush = time.monotonic()

    def add(self, record: dict) -> None:
        line = (json.dumps(record) + "\n").encode("utf-8")
        self._lines.append(line)
        self._size_bytes += len(line)

    def maybe_flush(self) -> None:
        if not self._lines:
            return
        elapsed = time.monotonic() - self._last_flush
        if self._size_bytes >= self._flush_size_bytes or elapsed >= self._flush_interval_seconds:
            self.flush()

    def flush(self) -> None:
        if not self._lines:
            return
        payload = gzip.compress(b"".join(self._lines))
        key = self._make_key()
        for attempt in range(1, self._max_retries + 1):
            try:
                self._object_store.put_object(key, payload)
                self._metrics.inc_storage_flush_total()
                self._metrics.inc_storage_bytes_total(len(payload))
                break
            except Exception:
                logger.exception("object store flush failed (attempt %d/%d)", attempt, self._max_retries)
                if attempt == self._max_retries:
                    self._metrics.inc_storage_errors_total()
        self._lines = []
        self._size_bytes = 0
        self._last_flush = time.monotonic()

    @staticmethod
    def _make_key() -> str:
        now = datetime.now(timezone.utc)
        return (
            f"logs/year={now:%Y}/month={now:%m}/day={now:%d}/hour={now:%H}/"
            f"{uuid.uuid4()}.ndjson.gz"
        )
