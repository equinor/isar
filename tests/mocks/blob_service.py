from pathlib import Path
from typing import List, Union

from isar.services.service_connections.azure.blob_service import BlobServiceInterface


class BlobServiceMock(BlobServiceInterface):
    def __init__(self) -> None:
        self.blob_paths: List[Path] = []

    def upload_blob(self, blob: Union[bytes, str], path_to_destination: Path) -> bool:
        self.blob_paths.append(path_to_destination)
        return True

    def blob_exists(self, path_to_blob: Path) -> bool:
        return path_to_blob in self.blob_paths
