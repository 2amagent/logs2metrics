from abc import ABC, abstractmethod

from logtriage.models import TemplateOut


class TemplateStore(ABC):
    """CRUD for template metadata, keyed on Drain3's stable cluster_id."""

    @abstractmethod
    def create_pending(self, cluster_id: int, template: str, sample_line: str) -> None:
        """Insert a new template row in 'pending' status, called on change_type == cluster_created."""

    @abstractmethod
    def update_template(self, cluster_id: int, template: str) -> None:
        """Update the stored template string for an existing cluster (cluster_template_changed). Does not touch status."""

    @abstractmethod
    def record_match(self, cluster_id: int, sample_line: str) -> None:
        """Bump match_count/last_seen for an existing cluster, topping up sample_lines under the configured cap."""

    @abstractmethod
    def get(self, cluster_id: int) -> TemplateOut | None:
        ...

    @abstractmethod
    def list(
        self,
        status: str | None = None,
        severity: str | None = None,
        muted: bool | None = None,
    ) -> list[TemplateOut]:
        ...

    @abstractmethod
    def categorize(
        self, cluster_id: int, severity: str, muted: bool, actor: str | None
    ) -> TemplateOut | None:
        """Set severity/muted, flip status -> categorized. Idempotent; re-categorization allowed."""

    @abstractmethod
    def count_pending(self) -> int:
        ...

    @abstractmethod
    def count_total(self) -> int:
        ...

    @abstractmethod
    def known_cluster_ids(self) -> set[int]:
        """All cluster_ids currently present in the store, used for startup reconciliation against Drain3 state."""
