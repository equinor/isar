import logging
from pathlib import Path
from typing import Union

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient

from isar.config.keyvault.keyvault_service import Keyvault
from isar.config.settings import settings
from isar.storage.storage_interface import StorageException, StorageInterface
from isar.storage.utilities import construct_metadata_file, construct_paths
from robot_interface.models.inspection.inspection import InspectionBlob
from robot_interface.models.mission.mission import Mission


class BlobStorage(StorageInterface):
    def __init__(self, keyvault: Keyvault) -> None:
        self.logger = logging.getLogger("uploader")

        storage_connection_string = keyvault.get_secret(
            "AZURE-STORAGE-CONNECTION-STRING"
        ).value

        if storage_connection_string is None:
            raise RuntimeError("AZURE-STORAGE-CONNECTION-STRING from keyvault is None")

        try:
            blob_service_client = BlobServiceClient.from_connection_string(
                storage_connection_string
            )
        except Exception as e:
            self.logger.error("Unable to retrieve blob service client. Error: %s", e)
            raise e

        self.container_client = blob_service_client.get_container_client(
            settings.BLOB_CONTAINER
        )

        if not self.container_client.exists():
            raise RuntimeError(
                "The configured blob container %s does not exist",
                settings.BLOB_CONTAINER,
            )

    def store(self, inspection: InspectionBlob, mission: Mission) -> Union[str, dict]:
        if inspection.data is None:
            raise StorageException("Nothing to store. The inspection data is empty")

        data_path, metadata_path = construct_paths(
            inspection=inspection, mission=mission
        )

        metadata_bytes: bytes = construct_metadata_file(
            inspection=inspection, mission=mission, filename=data_path.name
        )

        self._upload_file(path=metadata_path, data=metadata_bytes)
        return self._upload_file(path=data_path, data=inspection.data)

    def _upload_file(self, path: Path, data: bytes) -> Union[str, dict]:
        blob_client = self.container_client.get_blob_client(path.as_posix())
        try:
            blob_client.upload_blob(data=data)
        except ResourceExistsError as e:
            self.logger.error(
                f"Blob {path.as_posix()} already exists in container. Error: {e}"
            )
            raise StorageException from e
        except Exception as e:
            self.logger.error("An unexpected error occurred while uploading blob")
            raise StorageException from e

        absolute_inspection_path = {
            "source": "blob",
            "storage_account": settings.BLOB_STORAGE_ACCOUNT,
            "blob_container": settings.BLOB_CONTAINER,
            "blob_name": blob_client.blob_name,
        }
        return absolute_inspection_path
