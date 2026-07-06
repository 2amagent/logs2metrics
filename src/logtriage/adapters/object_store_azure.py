from logtriage.ports.object_store import ObjectStore


class AzureObjectStore(ObjectStore):
    """Stubbed adapter — Azure Blob support ships in Phase 2. Kept here to make the port contract visible."""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError("Azure adapter ships in Phase 2")

    def put_object(self, key: str, data: bytes) -> None:
        raise NotImplementedError("Azure adapter ships in Phase 2")
