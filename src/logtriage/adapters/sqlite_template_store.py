import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from logtriage.models import TemplateOut
from logtriage.ports.template_store import TemplateStore

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS templates (
    cluster_id      INTEGER PRIMARY KEY,
    template        TEXT NOT NULL,
    severity        TEXT NULL CHECK (severity IN ('error','warning','info') OR severity IS NULL),
    muted           INTEGER NOT NULL DEFAULT 0 CHECK (muted IN (0,1)),
    status          TEXT NOT NULL CHECK (status IN ('pending','categorized')),
    match_count     INTEGER NOT NULL DEFAULT 0,
    sample_lines    TEXT NOT NULL DEFAULT '[]',
    first_seen      TEXT NOT NULL,
    last_seen       TEXT NOT NULL,
    categorized_by  TEXT NULL,
    categorized_at  TEXT NULL
);
CREATE INDEX IF NOT EXISTS idx_templates_status ON templates(status);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_template(row: sqlite3.Row) -> TemplateOut:
    return TemplateOut(
        cluster_id=row["cluster_id"],
        template=row["template"],
        severity=row["severity"],
        muted=bool(row["muted"]),
        status=row["status"],
        match_count=row["match_count"],
        sample_lines=json.loads(row["sample_lines"]),
        first_seen=row["first_seen"],
        last_seen=row["last_seen"],
        categorized_by=row["categorized_by"],
        categorized_at=row["categorized_at"],
    )


class SqliteTemplateStore(TemplateStore):
    """Raw sqlite3 adapter. Single writer (the worker thread) by construction of the pipeline."""

    def __init__(self, db_path: str, sample_line_cap: int = 5):
        resolved_path = Path(db_path).resolve()
        logger.info("Opening SQLite template store at %s", resolved_path)
        try:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            logger.exception("Failed to create parent directory for SQLite db at %s", resolved_path)
            raise
        try:
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.executescript(SCHEMA)
            self._conn.commit()
        except sqlite3.Error:
            logger.exception("Failed to open/initialize SQLite db at %s", resolved_path)
            raise
        logger.info("SQLite template store ready at %s", resolved_path)
        self._sample_line_cap = sample_line_cap

    def create_pending(self, cluster_id: int, template: str, sample_line: str) -> None:
        now = _now()
        self._conn.execute(
            """INSERT INTO templates
                (cluster_id, template, status, match_count, sample_lines, first_seen, last_seen)
               VALUES (?, ?, 'pending', 1, ?, ?, ?)
               ON CONFLICT(cluster_id) DO NOTHING""",
            (cluster_id, template, json.dumps([sample_line]), now, now),
        )
        self._conn.commit()

    def update_template(self, cluster_id: int, template: str) -> None:
        self._conn.execute(
            "UPDATE templates SET template = ? WHERE cluster_id = ?",
            (template, cluster_id),
        )
        self._conn.commit()

    def record_match(self, cluster_id: int, sample_line: str) -> None:
        row = self._conn.execute(
            "SELECT sample_lines FROM templates WHERE cluster_id = ?", (cluster_id,)
        ).fetchone()
        if row is None:
            return
        samples = json.loads(row["sample_lines"])
        if len(samples) < self._sample_line_cap:
            samples.append(sample_line)
        self._conn.execute(
            """UPDATE templates
               SET match_count = match_count + 1, last_seen = ?, sample_lines = ?
               WHERE cluster_id = ?""",
            (_now(), json.dumps(samples), cluster_id),
        )
        self._conn.commit()

    def get(self, cluster_id: int) -> TemplateOut | None:
        row = self._conn.execute(
            "SELECT * FROM templates WHERE cluster_id = ?", (cluster_id,)
        ).fetchone()
        return _row_to_template(row) if row else None

    def list(
        self,
        status: str | None = None,
        severity: str | None = None,
        muted: bool | None = None,
    ) -> list[TemplateOut]:
        clauses = []
        params: list = []
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        if severity is not None:
            clauses.append("severity = ?")
            params.append(severity)
        if muted is not None:
            clauses.append("muted = ?")
            params.append(int(muted))
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            f"SELECT * FROM templates {where} ORDER BY last_seen DESC", params
        ).fetchall()
        return [_row_to_template(r) for r in rows]

    def categorize(
        self, cluster_id: int, severity: str, muted: bool, actor: str | None
    ) -> TemplateOut | None:
        cur = self._conn.execute(
            """UPDATE templates
               SET severity = ?, muted = ?, status = 'categorized',
                   categorized_by = ?, categorized_at = ?
               WHERE cluster_id = ?""",
            (severity, int(muted), actor, _now(), cluster_id),
        )
        self._conn.commit()
        if cur.rowcount == 0:
            return None
        return self.get(cluster_id)

    def count_pending(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM templates WHERE status = 'pending'"
        ).fetchone()
        return row["c"]

    def count_total(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS c FROM templates").fetchone()
        return row["c"]

    def known_cluster_ids(self) -> set[int]:
        rows = self._conn.execute("SELECT cluster_id FROM templates").fetchall()
        return {r["cluster_id"] for r in rows}
