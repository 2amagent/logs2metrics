from logtriage.ports.object_store import ObjectStore


class NullObjectStore(ObjectStore):
    """No-op adapter for object_store_backend: none. Enriched records are still
    counted into metrics; they're just never archived to any backend."""

    def put_object(self, key: str, data: bytes) -> None:
        pass
