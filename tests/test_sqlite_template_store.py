import pytest

from logtriage.adapters.sqlite_template_store import SqliteTemplateStore


@pytest.fixture
def store(tmp_path):
    return SqliteTemplateStore(str(tmp_path / "db.sqlite"), sample_line_cap=3)


def test_create_pending_then_get(store):
    store.create_pending(1, "hello <NUM>", "hello 1")
    row = store.get(1)
    assert row.status == "pending"
    assert row.template == "hello <NUM>"
    assert row.match_count == 1
    assert row.sample_lines == ["hello 1"]


def test_create_pending_is_idempotent_on_conflict(store):
    store.create_pending(1, "hello <NUM>", "hello 1")
    store.create_pending(1, "should not overwrite", "hello 2")
    row = store.get(1)
    assert row.template == "hello <NUM>"
    assert row.match_count == 1


def test_record_match_bumps_count_and_caps_samples(store):
    store.create_pending(1, "t", "line1")
    store.record_match(1, "line2")
    store.record_match(1, "line3")
    store.record_match(1, "line4")  # cap is 3, this one should not be appended

    row = store.get(1)
    assert row.match_count == 4
    assert row.sample_lines == ["line1", "line2", "line3"]


def test_update_template_does_not_change_status(store):
    store.create_pending(1, "old", "l")
    store.categorize(1, "error", False, "bob")
    store.update_template(1, "new template")
    row = store.get(1)
    assert row.template == "new template"
    assert row.status == "categorized"


def test_categorize_unknown_cluster_returns_none(store):
    assert store.categorize(999, "error", False, None) is None


def test_categorize_is_idempotent_and_re_categorizable(store):
    store.create_pending(1, "t", "l")
    store.categorize(1, "error", False, "bob")
    row = store.categorize(1, "warning", True, "alice")
    assert row.severity == "warning"
    assert row.muted is True
    assert row.categorized_by == "alice"
    assert row.status == "categorized"


def test_list_filters_by_status_severity_muted(store):
    store.create_pending(1, "t1", "l1")
    store.create_pending(2, "t2", "l2")
    store.categorize(2, "error", True, None)

    pending = store.list(status="pending")
    assert [r.cluster_id for r in pending] == [1]

    errors = store.list(severity="error")
    assert [r.cluster_id for r in errors] == [2]

    muted = store.list(muted=True)
    assert [r.cluster_id for r in muted] == [2]


def test_count_pending_and_total(store):
    store.create_pending(1, "t1", "l1")
    store.create_pending(2, "t2", "l2")
    store.categorize(2, "info", False, None)

    assert store.count_total() == 2
    assert store.count_pending() == 1


def test_known_cluster_ids(store):
    store.create_pending(1, "t1", "l1")
    store.create_pending(5, "t2", "l2")
    assert store.known_cluster_ids() == {1, 5}
