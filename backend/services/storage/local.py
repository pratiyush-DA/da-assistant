from pathlib import Path

from django.conf import settings

from .base import StorageBackend


class LocalStorageBackend(StorageBackend):
    def __init__(self):
        self.root = Path(settings.MEDIA_ROOT)
        self.root.mkdir(parents=True, exist_ok=True)

    def _full_path(self, key: str) -> Path:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def save(self, key: str, file_obj) -> str:
        path = self._full_path(key)
        with open(path, "wb") as dest:
            if hasattr(file_obj, "chunks"):
                for chunk in file_obj.chunks():
                    dest.write(chunk)
            else:
                dest.write(file_obj.read())
        return key

    def delete(self, key: str) -> None:
        path = self._full_path(key)
        if path.exists():
            path.unlink()

    def open(self, key: str):
        return open(self._full_path(key), "rb")
