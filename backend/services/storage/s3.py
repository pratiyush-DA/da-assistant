from .base import StorageBackend


class S3StorageBackend(StorageBackend):
    """Phase 2 — S3 storage backend stub."""

    def save(self, key: str, file_obj) -> str:
        raise NotImplementedError("S3 storage is not implemented yet.")

    def delete(self, key: str) -> None:
        raise NotImplementedError("S3 storage is not implemented yet.")

    def open(self, key: str):
        raise NotImplementedError("S3 storage is not implemented yet.")
