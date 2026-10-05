import logging
from pathlib import Path

from isar.config.settings import settings
from isar.storage.storage_interface import (
    LocalStoragePath,
    StorageException,
    StorageInterface,
)
from isar.storage.utilities import construct_path, inspection_bytes
from robot_interface.models.inspection.inspection import InspectionBlob, InspectionValue
from robot_interface.models.mission.mission import Mission


class LocalStorage(StorageInterface):
    def __init__(self) -> None:
        self.root_folder: Path = Path(settings.LOCAL_STORAGE_PATH)
        self.logger = logging.getLogger("uploader")

    def store(
        self, inspection: InspectionBlob | InspectionValue, mission: Mission
    ) -> LocalStoragePath:
        data = inspection_bytes(inspection)
        local_filename = construct_path(inspection=inspection, mission=mission)
        data_path: Path = self.root_folder.joinpath(local_filename)

        data_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(data_path, "wb") as file:
                file.write(data)
        except OSError as e:
            self.logger.warning(f"Failed open/write for file: {data_path}")
            raise StorageException from e
        except Exception as e:
            self.logger.error(
                "An unexpected error occurred while writing to local storage"
            )
            raise StorageException from e
        return LocalStoragePath(file_path=data_path)
