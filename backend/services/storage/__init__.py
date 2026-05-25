from django.conf import settings

from .base import StorageBackend
from .local import LocalStorageBackend
from .s3 import S3StorageBackend


def get_storage_backend() -> StorageBackend:
    backend = settings.STORAGE_BACKEND.lower()
    if backend == "local":
        return LocalStorageBackend()
    if backend == "s3":
        return S3StorageBackend()
    raise ValueError(f"Unknown STORAGE_BACKEND: {backend}")
