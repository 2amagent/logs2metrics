import time

from logtriage.worker.archive_buffer import ArchiveBuffer
from logtriage.worker.pipeline import PipelineWorker
from tests.fakes import FakeClusterer, FakeMetricsSink, FakeObjectStore, FakeTemplateStore


def test_worker_thread_processes_enqueued_records_end_to_end():
    store = FakeTemplateStore()
    metrics = FakeMetricsSink()
    clusterer = FakeClusterer()
    object_store = FakeObjectStore()
    buffer = ArchiveBuffer(object_store, metrics, flush_size_bytes=1, flush_interval_seconds=9999)

    worker = PipelineWorker(
        message_field="log",
        queue_max_size=100,
        clusterer=clusterer,
        store=store,
        metrics=metrics,
        buffer=buffer,
    )
    worker.start()
    try:
        assert worker.enqueue({"log": "disk full"})
        assert worker.enqueue({"log": "disk full"})

        deadline = time.monotonic() + 2
        while store.count_total() < 1 and time.monotonic() < deadline:
            time.sleep(0.01)

        row = store.get(1)
        assert row is not None
        assert row.match_count == 2
        assert object_store.objects  # buffer flushed given the size=1 threshold
    finally:
        worker.shutdown()

    assert clusterer.saved


def test_enqueue_returns_false_when_queue_full():
    store = FakeTemplateStore()
    metrics = FakeMetricsSink()
    clusterer = FakeClusterer()
    buffer = ArchiveBuffer(FakeObjectStore(), metrics, flush_size_bytes=10_000_000, flush_interval_seconds=9999)

    worker = PipelineWorker(
        message_field="log", queue_max_size=1, clusterer=clusterer, store=store, metrics=metrics, buffer=buffer
    )
    # do not start() the thread, so the queue never drains
    assert worker.enqueue({"log": "a"})
    assert not worker.enqueue({"log": "b"})
