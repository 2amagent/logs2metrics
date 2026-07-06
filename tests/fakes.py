from datetime import datetime, timezone

from logtriage.models import TemplateOut
from logtriage.ports.clusterer import ClusterResult, Clusterer
from logtriage.ports.metrics_sink import MetricsSink
from logtriage.ports.object_store import ObjectStore
from logtriage.ports.template_store import TemplateStore


def _now() -> datetime:
    return datetime.now(timezone.utc)


class FakeTemplateStore(TemplateStore):
    def __init__(self):
        self._rows: dict[int, dict] = {}

    def create_pending(self, cluster_id: int, template: str, sample_line: str) -> None:
        if cluster_id in self._rows:
            return
        now = _now()
        self._rows[cluster_id] = {
            "cluster_id": cluster_id,
            "template": template,
            "severity": None,
            "muted": False,
            "status": "pending",
            "match_count": 1,
            "sample_lines": [sample_line],
            "first_seen": now,
            "last_seen": now,
            "categorized_by": None,
            "categorized_at": None,
        }

    def update_template(self, cluster_id: int, template: str) -> None:
        if cluster_id in self._rows:
            self._rows[cluster_id]["template"] = template

    def record_match(self, cluster_id: int, sample_line: str) -> None:
        row = self._rows.get(cluster_id)
        if row is None:
            return
        row["match_count"] += 1
        row["last_seen"] = _now()
        if len(row["sample_lines"]) < 5:
            row["sample_lines"].append(sample_line)

    def get(self, cluster_id: int) -> TemplateOut | None:
        row = self._rows.get(cluster_id)
        return TemplateOut(**row) if row else None

    def list(self, status=None, severity=None, muted=None) -> list[TemplateOut]:
        out = []
        for row in self._rows.values():
            if status is not None and row["status"] != status:
                continue
            if severity is not None and row["severity"] != severity:
                continue
            if muted is not None and row["muted"] != muted:
                continue
            out.append(TemplateOut(**row))
        return out

    def categorize(self, cluster_id, severity, muted, actor) -> TemplateOut | None:
        row = self._rows.get(cluster_id)
        if row is None:
            return None
        row["severity"] = severity
        row["muted"] = muted
        row["status"] = "categorized"
        row["categorized_by"] = actor
        row["categorized_at"] = _now()
        return TemplateOut(**row)

    def count_pending(self) -> int:
        return sum(1 for r in self._rows.values() if r["status"] == "pending")

    def count_total(self) -> int:
        return len(self._rows)

    def known_cluster_ids(self) -> set[int]:
        return set(self._rows.keys())


class FakeObjectStore(ObjectStore):
    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def put_object(self, key: str, data: bytes) -> None:
        self.objects[key] = data


class FakeMetricsSink(MetricsSink):
    def __init__(self):
        self.logs_total: dict[tuple[str, bool], int] = {}
        self.ingested_total = 0
        self.new_templates_total = 0
        self.templates_pending = 0
        self.templates_total = 0
        self.queue_depth = 0
        self.processing_errors_total = 0
        self.storage_flush_total = 0
        self.storage_bytes_total = 0
        self.storage_errors_total = 0

    def inc_logs_total(self, severity: str, muted: bool) -> None:
        key = (severity, muted)
        self.logs_total[key] = self.logs_total.get(key, 0) + 1

    def inc_ingested_total(self, amount: int = 1) -> None:
        self.ingested_total += amount

    def inc_new_templates_total(self) -> None:
        self.new_templates_total += 1

    def set_templates_pending(self, value: int) -> None:
        self.templates_pending = value

    def set_templates_total(self, value: int) -> None:
        self.templates_total = value

    def set_queue_depth(self, value: int) -> None:
        self.queue_depth = value

    def inc_processing_errors_total(self) -> None:
        self.processing_errors_total += 1

    def inc_storage_flush_total(self) -> None:
        self.storage_flush_total += 1

    def inc_storage_bytes_total(self, amount: int) -> None:
        self.storage_bytes_total += amount

    def inc_storage_errors_total(self) -> None:
        self.storage_errors_total += 1


class FakeClusterer(Clusterer):
    """Deterministic fake: assigns cluster ids by exact-message dict key, with a
    scripted change_type sequence so tests can drive specific branches."""

    def __init__(self):
        self._next_id = 1
        self._known: dict[str, int] = {}
        self.saved = False
        self.forced_result: ClusterResult | None = None

    def add_log_message(self, message: str) -> ClusterResult:
        if self.forced_result is not None:
            result = self.forced_result
            self.forced_result = None
            return result
        if message not in self._known:
            cluster_id = self._next_id
            self._next_id += 1
            self._known[message] = cluster_id
            return ClusterResult(
                change_type="cluster_created",
                cluster_id=cluster_id,
                cluster_size=1,
                template_mined=message,
                cluster_count=len(self._known),
            )
        cluster_id = self._known[message]
        return ClusterResult(
            change_type="none",
            cluster_id=cluster_id,
            cluster_size=2,
            template_mined=message,
            cluster_count=len(self._known),
        )

    def save_state(self) -> None:
        self.saved = True

    def known_cluster_ids(self) -> set[int]:
        return set(self._known.values())
