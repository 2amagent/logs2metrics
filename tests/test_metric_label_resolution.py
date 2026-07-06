from logtriage.worker.archive_buffer import ArchiveBuffer
from logtriage.worker.pipeline import process_record
from tests.fakes import FakeClusterer, FakeMetricsSink, FakeObjectStore, FakeTemplateStore


def test_pending_template_resolves_to_uncategorized_false():
    store = FakeTemplateStore()
    metrics = FakeMetricsSink()
    clusterer = FakeClusterer()
    buffer = ArchiveBuffer(FakeObjectStore(), metrics, flush_size_bytes=10_000_000, flush_interval_seconds=9999)

    process_record({"log": "boom"}, "log", clusterer, store, metrics, buffer)

    assert metrics.logs_total == {("uncategorized", False): 1}


def test_categorized_template_resolves_to_stored_severity_and_muted():
    store = FakeTemplateStore()
    metrics = FakeMetricsSink()
    clusterer = FakeClusterer()
    buffer = ArchiveBuffer(FakeObjectStore(), metrics, flush_size_bytes=10_000_000, flush_interval_seconds=9999)

    process_record({"log": "boom"}, "log", clusterer, store, metrics, buffer)
    store.categorize(1, severity="warning", muted=True, actor=None)

    process_record({"log": "boom"}, "log", clusterer, store, metrics, buffer)

    assert metrics.logs_total[("warning", True)] == 1
    assert ("uncategorized", False) in metrics.logs_total  # from the first, pre-categorize match
