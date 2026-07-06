from pathlib import Path

from logtriage.ports.object_store import ObjectStore


class LocalObjectStore(ObjectStore):
    """Dev adapter: writes archive objects under a local directory, mirroring the key layout as a relative path."""

    def __init__(self, data_dir: str):
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)

    def put_object(self, key: str, data: bytes) -> None:
        path = self._data_dir / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
