from injector import Module, provider, singleton

from isar.storage.storage_interface import StorageInterface
from tests.mocks.blob_storage import BlobStorageMock


class MockStorageModule(Module):
    @provider
    @singleton
    def provide_storage(self) -> StorageInterface:
        return BlobStorageMock()
