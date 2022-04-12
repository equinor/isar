import logging
from pathlib import Path

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobClient, BlobServiceClient, ContainerClient
from injector import inject

from isar.config.keyvault.keyvault_service import Keyvault
from isar.config.settings import settings
from isar.models.mission_metadata.mission_metadata import MissionMetadata
from isar.storage.storage_interface import StorageException, StorageInterface
from isar.storage.utilities import construct_local_paths, construct_metadata_file
from robot_interface.models.inspection.inspection import Inspection


class BlobStorage(StorageInterface):
    @inject
    def __init__(
        self, keyvault: Keyvault, container_name: str = settings.BLOB_CONTAINER
    ):
        self.keyvault = keyvault
        self.storage_connection_string = self.keyvault.get_secret(
            "AZURE-STORAGE-CONNECTION-STRING"
        ).value
        self.container_name = container_name

        self.blob_service_client = self._get_blob_service_client()
        self.container_client = self._get_container_client(
            blob_service_client=self.blob_service_client
        )

        self.logger = logging.getLogger("uploader")

    def store(self, inspection: Inspection, metadata: MissionMetadata):
        local_path, local_metadata_path = construct_local_paths(
            inspection=inspection, metadata=metadata
        )

        metadata_bytes: bytes = construct_metadata_file(
            inspection=inspection, metadata=metadata, filename=local_path.name
        )

        self._upload_file(path=local_path, data=inspection.data)
        self._upload_file(path=local_metadata_path, data=metadata_bytes)

    def _upload_file(self, path: Path, data: bytes):
        blob_client = self._get_blob_client(path)
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

    def _get_blob_service_client(self) -> BlobServiceClient:
        try:
            return BlobServiceClient.from_connection_string(
                self.storage_connection_string
            )
        except Exception as e:
            self.logger.error(f"Unable to retrieve blob service client. Error: {e}")
            raise e

    def _get_container_client(
        self, blob_service_client: BlobServiceClient
    ) -> ContainerClient:
        return blob_service_client.get_container_client(self.container_name)

    def _get_blob_client(self, path_to_blob: Path) -> BlobClient:
        return self.container_client.get_blob_client(path_to_blob.as_posix())
