from pathlib import Path
from typing import List

from isar.storage.storage_interface import StorageInterface


class BlobStorageMock(StorageInterface):
    def __init__(self) -> None:
        self.blob_paths: List[Path] = []

    def store(self, data: bytes, path: Path) -> bool:
        self.blob_paths.append(path)
        return True

    def blob_exists(self, path_to_blob: Path) -> bool:
        return path_to_blob in self.blob_paths
