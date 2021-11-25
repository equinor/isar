from pathlib import Path

from isar.config import config
from isar.storage.storage_interface import StorageInterface


class LocalStorage(StorageInterface):
    def __init__(self):
        self.root_folder: Path = Path(config.get("DEFAULT", "local_storage_path"))

    def store(self, data: bytes, path: Path):
        filename: Path = self.root_folder.joinpath(path)

        filename.parent.mkdir(parents=True, exist_ok=True)

        with open(filename, "wb") as f:
            f.write(data)
