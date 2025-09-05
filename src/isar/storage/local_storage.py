import logging
from pathlib import Path

from isar.config.settings import settings
from isar.storage.storage_interface import (
    LocalStoragePath,
    StorageException,
    StorageInterface,
    StoragePaths,
)
from isar.storage.utilities import construct_metadata_file, construct_paths
from robot_interface.models.inspection.inspection import InspectionBlob
from robot_interface.models.mission.mission import Mission


class LocalStorage(StorageInterface):
    def __init__(self) -> None:
        self.root_folder: Path = Path(settings.LOCAL_STORAGE_PATH)
        self.logger = logging.getLogger("uploader")

    def store(
        self, inspection: InspectionBlob, mission: Mission
    ) -> StoragePaths[LocalStoragePath]:
        if inspection.data is None:
            raise StorageException("Nothing to store. The inspection data is empty")

        local_filename, local_metadata_filename = construct_paths(
            inspection=inspection, mission=mission
        )

        data_path: Path = self.root_folder.joinpath(local_filename)
        metadata_path: Path = self.root_folder.joinpath(local_metadata_filename)

        data_path.parent.mkdir(parents=True, exist_ok=True)

        metadata_bytes: bytes = construct_metadata_file(
            inspection=inspection, mission=mission, filename=local_filename.name
        )
        try:
            with (
                open(data_path, "wb") as file,
                open(metadata_path, "wb") as metadata_file,
            ):
                file.write(inspection.data)
                metadata_file.write(metadata_bytes)
        except IOError as e:
            self.logger.warning(
                f"Failed open/write for one of the following files: \n"
                f"{data_path}\n{metadata_path}"
            )
            raise StorageException from e
        except Exception as e:
            self.logger.error(
                "An unexpected error occurred while writing to local storage"
            )
            raise StorageException from e
        return StoragePaths(
            data_path=LocalStoragePath(file_path=data_path),
            metadata_path=LocalStoragePath(file_path=metadata_path),
        )
