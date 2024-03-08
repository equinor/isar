import os
from isar.config.keyvault.keyvault_service import Keyvault
from isar.config.settings import settings
from isar.storage.blob_storage import BlobStorage


class TestBlobdownload:
    def __init__(self):
        self.keyvault: Keyvault = Keyvault(
            keyvault_name=settings.KEYVAULT_NAME,
            client_id=settings.AZURE_CLIENT_ID,
            client_secret=None,
            tenant_id=settings.AZURE_TENANT_ID,
        )

        self.storage_connection_string = self.keyvault.get_secret(
            "AZURE-STORAGE-CONNECTION-STRING"
        ).value
        self.container_name = settings.BLOB_CONTAINER

        self.blob_storage = BlobStorage(
            keyvault=self.keyvault, container_name=self.container_name
        )

    def test_blob_download(self, download_file_path: str, blob_name: str) -> None:
        blob_service_client = self.blob_storage._get_blob_service_client()
        container_client = self.blob_storage._get_container_client(
            blob_service_client=blob_service_client
        )

        print("\nDownloading blob to \n\t" + download_file_path)
        with open(file=download_file_path, mode="wb") as download_file:
            download_file.write(container_client.download_blob(blob_name).readall())


if __name__ == "__main__":
    # replace with exact name that is being sent as inspection_path over the mqtt broker
    blob_name: str = ""
    download_file_path = os.path.join(r"\Downloads", "example.jpg")

    blob: TestBlobdownload = TestBlobdownload()
    blob.test_blob_download(download_file_path=download_file_path, blob_name=blob_name)
