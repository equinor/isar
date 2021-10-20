from injector import Module, provider, singleton

from isar.services.service_connections.mqtt.mqtt_service_interface import (
    MQTTServiceInterface,
)
from isar.storage.storage_interface import StorageInterface
from tests.mocks.blob_storage import StorageMock
from tests.mocks.mqtt_service import MQTTServiceMock


class MockStorageModule(Module):
    @provider
    @singleton
    def provide_storage(self) -> StorageInterface:
        return StorageMock()


class MockMQTTServiceModule(Module):
    @provider
    @singleton
    def provide_mqtt(self) -> MQTTServiceInterface:
        return MQTTServiceMock()
