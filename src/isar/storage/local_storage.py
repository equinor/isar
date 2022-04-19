import logging
from pathlib import Path

from isar.config.settings import settings
from isar.models.mission_metadata.mission_metadata import MissionMetadata
from isar.storage.storage_interface import StorageException, StorageInterface
from isar.storage.utilities import construct_local_paths, construct_metadata_file
from robot_interface.models.inspection.inspection import Inspection


class LocalStorage(StorageInterface):
    def __init__(self):
        self.root_folder: Path = Path(settings.LOCAL_STORAGE_PATH)
        self.logger = logging.getLogger("uploader")

    def store(self, inspection: Inspection, metadata: MissionMetadata):
        local_path, local_metadata_path = construct_local_paths(
            inspection=inspection, metadata=metadata
        )

        absolute_path: Path = self.root_folder.joinpath(local_path)
        absolute_metadata_path: Path = self.root_folder.joinpath(local_metadata_path)

        absolute_path.parent.mkdir(parents=True, exist_ok=True)

        metadata_bytes: bytes = construct_metadata_file(
            inspection=inspection, metadata=metadata, filename=local_path.name
        )
        try:
            with open(absolute_path, "wb") as file, open(
                absolute_metadata_path, "wb"
            ) as metadata_file:
                file.write(inspection.data)
                metadata_file.write(metadata_bytes)
        except IOError as e:
            self.logger.warning(
                f"Failed open/write for one of the following files: \n"
                f"{absolute_path}\n{absolute_metadata_path}"
            )
            raise StorageException from e
        except Exception as e:
            self.logger.error(
                "An unexpected error occurred while writing to local storage"
            )
            raise StorageException from e
