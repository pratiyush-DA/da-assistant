from abc import ABC, abstractmethod
from typing import BinaryIO


class StorageBackend(ABC):
    @abstractmethod
    def save(self, key: str, file_obj) -> str:
        """Persist file and return storage key."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove file at key."""

    @abstractmethod
    def open(self, key: str) -> BinaryIO:
        """Open file for reading."""
