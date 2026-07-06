from logtriage.ports.clusterer import ClusterResult
from logtriage.worker.archive_buffer import ArchiveBuffer
from logtriage.worker.pipeline import process_record
from tests.fakes import FakeClusterer, FakeMetricsSink, FakeObjectStore, FakeTemplateStore


def make_deps():
    store = FakeTemplateStore()
    metrics = FakeMetricsSink()
    clusterer = FakeClusterer()
    object_store = FakeObjectStore()
    buffer = ArchiveBuffer(object_store, metrics, flush_size_bytes=10_000_000, flush_interval_seconds=9999)
    return store, metrics, clusterer, object_store, buffer


def test_cluster_created_marks_pending_and_counts_new_template():
    store, metrics, clusterer, object_store, buffer = make_deps()

    process_record({"log": "hello world"}, "log", clusterer, store, metrics, buffer)

    row = store.get(1)
    assert row.status == "pending"
    assert row.match_count == 1
    assert metrics.new_templates_total == 1
    assert metrics.logs_total[("uncategorized", False)] == 1


def test_repeated_message_bumps_match_count_without_reopening_review():
    store, metrics, clusterer, object_store, buffer = make_deps()

    process_record({"log": "hello world"}, "log", clusterer, store, metrics, buffer)
    process_record({"log": "hello world"}, "log", clusterer, store, metrics, buffer)

    row = store.get(1)
    assert row.status == "pending"
    assert row.match_count == 2
    assert metrics.new_templates_total == 1  # only counted once


def test_cluster_template_changed_updates_template_but_not_status():
    store, metrics, clusterer, object_store, buffer = make_deps()
    process_record({"log": "hello world"}, "log", clusterer, store, metrics, buffer)

    row = store.get(1)
    assert row.status == "pending"

    clusterer.forced_result = ClusterResult(
        change_type="cluster_template_changed",
        cluster_id=1,
        cluster_size=2,
        template_mined="hello <NUM>",
        cluster_count=1,
    )
    process_record({"log": "hello 42"}, "log", clusterer, store, metrics, buffer)

    row = store.get(1)
    assert row.template == "hello <NUM>"
    assert row.status == "pending"  # refining an existing cluster must not reopen review
    assert row.match_count == 2


def test_categorized_cluster_resolves_stored_severity_and_muted():
    store, metrics, clusterer, object_store, buffer = make_deps()
    process_record({"log": "hello world"}, "log", clusterer, store, metrics, buffer)
    store.categorize(1, severity="error", muted=True, actor="alice")

    process_record({"log": "hello world"}, "log", clusterer, store, metrics, buffer)

    assert metrics.logs_total[("error", True)] == 1


def test_enriched_record_lands_in_archive_buffer():
    store, metrics, clusterer, object_store, buffer = make_deps()
    process_record({"log": "hello world"}, "log", clusterer, store, metrics, buffer)

    assert len(buffer._lines) == 1
    import json

    line = json.loads(buffer._lines[0])
    assert line["cluster_id"] == 1
    assert line["severity"] == "uncategorized"
    assert line["muted"] is False
    assert line["log"] == "hello world"
