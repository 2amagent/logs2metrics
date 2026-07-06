from abc import ABC, abstractmethod


class ObjectStore(ABC):
    """Write-only archival sink. No vendor SDK types leak past this boundary."""

    @abstractmethod
    def put_object(self, key: str, data: bytes) -> None:
        ...
