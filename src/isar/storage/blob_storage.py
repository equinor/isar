import logging
from pathlib import Path

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import BlobClient, BlobServiceClient, ContainerClient
from injector import inject

from isar.config import config
from isar.config.keyvault.keyvault_service import Keyvault
from isar.storage.storage_interface import StorageInterface


class BlobStorage(StorageInterface):
    @inject
    def __init__(
        self,
        keyvault: Keyvault,
        container_name: str = config.get("service_connections", "blob_container"),
    ):
        self.keyvault = keyvault
        self.storage_connection_string = self.keyvault.get_secret(
            "AZURE-STORAGE-CONNECTION-STRING"
        ).value
        self.container_name = container_name

        self.blob_service_client = self.get_blob_service_client()
        self.container_client = self.get_container_client()

    def store(self, data: bytes, path: Path) -> bool:
        blob_client = self.get_blob_client(path)
        try:
            blob_client.upload_blob(data)
            return True
        except ResourceExistsError as e:
            logging.error(
                f"Blob {path.as_posix()} already exists in container. Error: {e}"
            )
            return False
        except Exception as e:
            logging.error(
                f"An error occurred while uploading blob from file. Error: {e}"
            )
            return False

    def blob_exists(self, path_to_blob: Path) -> bool:
        blob_client = self.get_blob_client(path_to_blob)
        try:
            blob_client.get_blob_properties()
            return True
        except ResourceNotFoundError:
            return False

    def get_blob_service_client(self) -> BlobServiceClient:
        try:
            return BlobServiceClient.from_connection_string(
                self.storage_connection_string
            )
        except Exception as e:
            logging.error(f"Unable to retrieve blob service client. Error: {e}")
            raise e

    def get_container_client(self) -> ContainerClient:
        return self.blob_service_client.get_container_client(self.container_name)

    def get_blob_client(self, path_to_blob: Path) -> BlobClient:
        return self.container_client.get_blob_client(path_to_blob.as_posix())
