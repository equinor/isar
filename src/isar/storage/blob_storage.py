import logging
from pathlib import Path

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient, ContainerClient

from isar.config.keyvault.keyvault_service import Keyvault
from isar.config.settings import settings
from isar.storage.storage_interface import (
    BlobStoragePath,
    StorageException,
    StorageInterface,
    StoragePaths,
)
from isar.storage.utilities import construct_metadata_file, construct_paths
from robot_interface.models.inspection.inspection import InspectionBlob
from robot_interface.models.mission.mission import Mission


class BlobStorage(StorageInterface):
    def __init__(self, keyvault: Keyvault) -> None:
        self.logger = logging.getLogger("uploader")

        self.container_client_data = self._get_container_client(
            keyvault, "AZURE-STORAGE-CONNECTION-STRING-DATA"
        )
        self.container_client_metadata = self._get_container_client(
            keyvault, "AZURE-STORAGE-CONNECTION-STRING-METADATA"
        )

    def _get_container_client(self, keyvault: Keyvault, secret_name: str):
        storage_connection_string = keyvault.get_secret(secret_name).value

        if storage_connection_string is None:
            raise RuntimeError(f"{secret_name} from keyvault is None")

        try:
            blob_service_client = BlobServiceClient.from_connection_string(
                storage_connection_string
            )
        except Exception as e:
            self.logger.error("Unable to retrieve blob service client. Error: %s", e)
            raise e

        container_client = blob_service_client.get_container_client(
            settings.BLOB_CONTAINER
        )

        if not container_client.exists():
            raise RuntimeError(
                "The configured blob container %s does not exist",
                settings.BLOB_CONTAINER,
            )
        return container_client

    def store(
        self, inspection: InspectionBlob, mission: Mission
    ) -> StoragePaths[BlobStoragePath]:
        if inspection.data is None:
            raise StorageException("Nothing to store. The inspection data is empty")

        data_filename, metadata_filename = construct_paths(
            inspection=inspection, mission=mission
        )

        metadata_bytes: bytes = construct_metadata_file(
            inspection=inspection, mission=mission, filename=data_filename.name
        )

        data_path = self._upload_file(
            filename=data_filename,
            data=inspection.data,
            container_client=self.container_client_data,
        )
        metadata_path = self._upload_file(
            filename=metadata_filename,
            data=metadata_bytes,
            container_client=self.container_client_metadata,
        )
        return StoragePaths(data_path=data_path, metadata_path=metadata_path)

    def _upload_file(
        self, filename: Path, data: bytes, container_client: ContainerClient
    ) -> BlobStoragePath:
        blob_client = container_client.get_blob_client(filename.as_posix())
        try:
            blob_client.upload_blob(data=data)
        except ResourceExistsError as e:
            self.logger.error(
                "Blob %s already exists in container. Error: %s", filename.as_posix(), e
            )
            raise StorageException from e
        except Exception as e:
            self.logger.error("An unexpected error occurred while uploading blob")
            raise StorageException from e

        return BlobStoragePath(
            storage_account=settings.BLOB_STORAGE_ACCOUNT,
            blob_container=settings.BLOB_CONTAINER,
            blob_name=blob_client.blob_name,
        )
