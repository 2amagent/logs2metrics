from abc import ABC, abstractmethod
from typing import TypedDict


class ClusterResult(TypedDict):
    change_type: str  # "cluster_created" | "cluster_template_changed" | "none"
    cluster_id: int
    cluster_size: int
    template_mined: str
    cluster_count: int


class Clusterer(ABC):
    """Wraps Drain3. Single owner: only the worker thread may call add_log_message."""

    @abstractmethod
    def add_log_message(self, message: str) -> ClusterResult:
        ...

    @abstractmethod
    def save_state(self) -> None:
        ...
