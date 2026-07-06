from abc import ABC, abstractmethod


class MetricsSink(ABC):
    """Thin wrapper over the metrics backend so the pipeline/tests never import prometheus_client directly."""

    @abstractmethod
    def inc_logs_total(self, severity: str, muted: bool) -> None:
        ...

    @abstractmethod
    def inc_ingested_total(self, amount: int = 1) -> None:
        ...

    @abstractmethod
    def inc_new_templates_total(self) -> None:
        ...

    @abstractmethod
    def set_templates_pending(self, value: int) -> None:
        ...

    @abstractmethod
    def set_templates_total(self, value: int) -> None:
        ...

    @abstractmethod
    def set_queue_depth(self, value: int) -> None:
        ...

    @abstractmethod
    def inc_processing_errors_total(self) -> None:
        ...

    @abstractmethod
    def inc_storage_flush_total(self) -> None:
        ...

    @abstractmethod
    def inc_storage_bytes_total(self, amount: int) -> None:
        ...

    @abstractmethod
    def inc_storage_errors_total(self) -> None:
        ...
