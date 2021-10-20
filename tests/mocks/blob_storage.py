from pathlib import Path
from typing import List

from isar.storage.storage_interface import StorageInterface


class StorageMock(StorageInterface):
    def __init__(self) -> None:
        self.paths: List[Path] = []

    def store(self, data: bytes, path: Path) -> bool:
        self.paths.append(path)
        return True

    def blob_exists(self, path: Path) -> bool:
        return path in self.paths
