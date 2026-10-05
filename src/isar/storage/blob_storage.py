import logging
from pathlib import Path

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient, ContainerClient

from isar.config.settings import settings
from isar.storage.storage_interface import (
    BlobStoragePath,
    StorageException,
    StorageInterface,
)
from isar.storage.utilities import construct_path, inspection_bytes
from robot_interface.models.inspection.inspection import InspectionBlob, InspectionValue
from robot_interface.models.mission.mission import Mission


class BlobStorage(StorageInterface):
    def __init__(self) -> None:
        self.logger = logging.getLogger("uploader")

        self.container_client_data = self._get_container_client(
            settings.BLOB_STORAGE_ACCOUNT_DATA,
            settings.BLOB_STORAGE_CONNECTION_STRING_DATA,
        )

    def _get_container_client(
        self, account_name: str, storage_connection_string: str
    ) -> ContainerClient:

        if not storage_connection_string:
            raise RuntimeError("BlobStorage connection string is Empty or None")

        try:
            blob_service_client = BlobServiceClient.from_connection_string(
                storage_connection_string
            )
            if blob_service_client.account_name != account_name:
                raise StorageException(
                    f"The blob storage in the connection string does not match the settings for blob storage account {account_name}"
                )
        except (StorageException, ValueError) as e:
            self.logger.error("Unable to retrieve blob service client. Error: %s", e)
            raise

        container_client: ContainerClient = blob_service_client.get_container_client(
            settings.BLOB_CONTAINER
        )

        if not container_client.exists():
            raise RuntimeError(
                "The configured blob container %s does not exist",
                settings.BLOB_CONTAINER,
            )
        return container_client

    def store(
        self, inspection: InspectionBlob | InspectionValue, mission: Mission
    ) -> BlobStoragePath:
        data = inspection_bytes(inspection)
        data_filename = construct_path(inspection=inspection, mission=mission)

        return self._upload_file(
            filename=data_filename,
            data=data,
            container_client=self.container_client_data,
            account_name=settings.BLOB_STORAGE_ACCOUNT_DATA,
        )

    def _upload_file(
        self,
        filename: Path,
        data: bytes,
        container_client: ContainerClient,
        account_name: str,
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
            self.logger.error(
                "An unexpected error occurred while uploading blob: %s", e
            )
            raise StorageException from e

        return BlobStoragePath(
            storage_account=account_name,
            blob_container=settings.BLOB_CONTAINER,
            blob_name=blob_client.blob_name,
        )
