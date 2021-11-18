from injector import Module, provider, singleton

from isar.storage.storage_interface import StorageInterface
from robot_interface.robot_interface import RobotInterface
from tests.mocks.blob_storage import StorageMock
from tests.mocks.robot_interface import MockRobot


class MockStorageModule(Module):
    @provider
    @singleton
    def provide_storage(self) -> StorageInterface:
        return StorageMock()


class MockRobotModule(Module):
    @provider
    @singleton
    def provide_robot(self) -> RobotInterface:
        return MockRobot()
