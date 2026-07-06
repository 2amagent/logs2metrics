from prometheus_client import CollectorRegistry, Counter, Gauge

from logtriage.ports.metrics_sink import MetricsSink


class PrometheusMetricsSink(MetricsSink):
    """Owns all Prometheus metric objects. Counter/Gauge .inc()/.set() are thread-safe by default
    (internal MutexValue lock), so the worker thread and async request handlers can share this safely."""

    def __init__(self, registry: CollectorRegistry | None = None):
        kwargs = {"registry": registry} if registry is not None else {}

        self.logs_total = Counter(
            "logtriage_logs_total",
            "Logs counted by resolved severity/mute bucket",
            ["severity", "muted"],
            **kwargs,
        )
        self.ingested_total = Counter(
            "logtriage_ingested_total", "Raw records received via /ingest", **kwargs
        )
        self.new_templates_total = Counter(
            "logtriage_new_templates_total", "Drain3 cluster_created events", **kwargs
        )
        self.templates_pending = Gauge(
            "logtriage_templates_pending", "Templates awaiting categorization", **kwargs
        )
        self.templates_total = Gauge(
            "logtriage_templates_total", "Total known templates/clusters", **kwargs
        )
        self.queue_depth = Gauge(
            "logtriage_queue_depth", "Ingest to worker queue backlog", **kwargs
        )
        self.processing_errors_total = Counter(
            "logtriage_processing_errors_total", "Errors while processing a queued record", **kwargs
        )
        self.storage_flush_total = Counter(
            "logtriage_storage_flush_total", "Object-store buffer flushes", **kwargs
        )
        self.storage_bytes_total = Counter(
            "logtriage_storage_bytes_total", "Bytes written to object storage", **kwargs
        )
        self.storage_errors_total = Counter(
            "logtriage_storage_errors_total", "Object-store write failures", **kwargs
        )

    def inc_logs_total(self, severity: str, muted: bool) -> None:
        self.logs_total.labels(severity=severity, muted=str(muted).lower()).inc()

    def inc_ingested_total(self, amount: int = 1) -> None:
        self.ingested_total.inc(amount)

    def inc_new_templates_total(self) -> None:
        self.new_templates_total.inc()

    def set_templates_pending(self, value: int) -> None:
        self.templates_pending.set(value)

    def set_templates_total(self, value: int) -> None:
        self.templates_total.set(value)

    def set_queue_depth(self, value: int) -> None:
        self.queue_depth.set(value)

    def inc_processing_errors_total(self) -> None:
        self.processing_errors_total.inc()

    def inc_storage_flush_total(self) -> None:
        self.storage_flush_total.inc()

    def inc_storage_bytes_total(self, amount: int) -> None:
        self.storage_bytes_total.inc(amount)

    def inc_storage_errors_total(self) -> None:
        self.storage_errors_total.inc()
