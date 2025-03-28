from typing import List

from dependency_injector import containers
from dependency_injector.wiring import providers

from isar.apis.security.authentication import Authenticator
from isar.storage.storage_interface import StorageInterface
from robot_interface.robot_interface import RobotInterface
from robot_interface.telemetry.mqtt_client import MqttClientInterface
from tests.mocks.blob_storage import StorageMock
from tests.mocks.mqtt_client import MqttClientMock
from tests.mocks.robot_interface import MockRobot


class MockContainer(containers.DeclarativeContainer):
    storage_provider = providers.List(providers.Singleton(StorageMock))

    mqtt_provider = providers.Singleton(MqttClientMock)

    robot_provider = providers.Singleton(MockRobot)

    no_authentication_provider = providers.Singleton(
        Authenticator, authentication_enabled=False
    )

    authentication_provider = providers.Singleton(
        Authenticator, authentication_enabled=True
    )
