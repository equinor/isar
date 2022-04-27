from typing import List

from injector import Module, multiprovider, provider, singleton

from isar.apis.security.authentication import Authenticator
from isar.storage.storage_interface import StorageInterface
from robot_interface.robot_interface import RobotInterface
from tests.mocks.blob_storage import StorageMock
from tests.mocks.robot_interface import MockRobot


class MockStorageModule(Module):
    @multiprovider
    @singleton
    def provide_storage(self) -> List[StorageInterface]:
        return [StorageMock()]


class MockRobotModule(Module):
    @provider
    @singleton
    def provide_robot(self) -> RobotInterface:
        return MockRobot()


class MockNoAuthenticationModule(Module):
    @provider
    @singleton
    def provide_authenticator(self) -> Authenticator:
        return Authenticator(authentication_enabled=False)


class MockAuthenticationModule(Module):
    @provider
    @singleton
    def provide_authenticator(self) -> Authenticator:
        return Authenticator(authentication_enabled=True)
