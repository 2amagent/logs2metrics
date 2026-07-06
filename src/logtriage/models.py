from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Severity = Literal["error", "warning", "info"]
Status = Literal["pending", "categorized"]


class IngestRecord(BaseModel):
    """A single raw record accepted by POST /ingest, before enrichment."""

    model_config = {"extra": "allow"}

    log: str | None = None
    message: str | None = None


class EnrichedRecord(BaseModel):
    """An IngestRecord after clustering + categorization resolution, ready for archival."""

    model_config = {"extra": "allow"}

    cluster_id: int
    severity: str
    muted: bool


class TemplateOut(BaseModel):
    cluster_id: int
    template: str
    severity: Severity | None
    muted: bool
    status: Status
    match_count: int
    sample_lines: list[str]
    first_seen: datetime
    last_seen: datetime
    categorized_by: str | None
    categorized_at: datetime | None


class CategorizeRequest(BaseModel):
    severity: Severity
    muted: bool = False
    actor: str | None = None


class TemplateListFilter(BaseModel):
    status: Status | None = None
    severity: Severity | None = None
    muted: bool | None = None
