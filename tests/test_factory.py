import pytest

from logtriage.adapters.object_store_local import LocalObjectStore
from logtriage.adapters.object_store_null import NullObjectStore
from logtriage.adapters.object_store_s3 import S3ObjectStore
from logtriage.config import Settings
from logtriage.factory import build_object_store


def test_none_backend_returns_null_object_store():
    settings = Settings(object_store_backend="none")
    store = build_object_store(settings)
    assert isinstance(store, NullObjectStore)
    store.put_object("some/key", b"data")  # no-op, must not raise


def test_default_backend_is_none():
    assert Settings().object_store_backend == "none"


def test_local_backend_returns_local_object_store(tmp_path):
    settings = Settings(object_store_backend="local")
    settings.local.data_dir = str(tmp_path)
    store = build_object_store(settings)
    assert isinstance(store, LocalObjectStore)


def test_s3_backend_returns_s3_object_store():
    settings = Settings(object_store_backend="s3")
    store = build_object_store(settings)
    assert isinstance(store, S3ObjectStore)


def test_unknown_backend_raises():
    with pytest.raises(ValueError):
        Settings(object_store_backend="bogus")
