import shutil
from pathlib import Path

import pytest
from dependency_injector.wiring import providers
from fastapi.testclient import TestClient

from isar.apis.security.authentication import Authenticator
from isar.config import settings
from isar.modules import ApplicationContainer
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.idle import Idle
from isar.state_machine.states.monitor import Monitor
from isar.storage.uploader import Uploader
from tests.isar.state_machine.test_state_machine import (
    RobotServiceThread,
    StateMachineThread,
    UploaderThread,
)
from tests.mocks.blob_storage import StorageMock
from tests.mocks.mqtt_client import MqttClientMock
from tests.mocks.robot_interface import MockRobot


@pytest.fixture()
def container():
    """Fixture to provide the dependency-injector container without auth."""
    container = ApplicationContainer()
    container.storage_handlers.override(providers.List([StorageMock]))
    container.mqtt_client.override(providers.Singleton(MqttClientMock))
    container.robot.override(providers.Singleton(MockRobot))
    container.uploader.override(
        providers.Singleton(
            Uploader,
            container.events(),
            container.storage_handlers(),
            container.mqtt_client(),
        )
    )
    return container


@pytest.fixture()
def app(container: ApplicationContainer):
    """Fixture to provide the FastAPI app."""
    container.authenticator.override(
        providers.Singleton(Authenticator, authentication_enabled=False)
    )

    app = container.api().get_app()
    return app


@pytest.fixture()
def client(app):
    """Fixture to provide a test client for the FastAPI app."""
    client = TestClient(app)
    return client


@pytest.fixture()
def client_auth(container: ApplicationContainer):
    """Fixture to provide a test client for the FastAPI app with auth."""
    container.authenticator.override(
        providers.Singleton(Authenticator, authentication_enabled=True)
    )

    app = container.api().get_app()
    client = TestClient(app)
    return client


@pytest.fixture()
def access_token():
    """Fixture to provide a dummy access token."""
    return "DummyToken"


@pytest.fixture()
def keyvault(container: ApplicationContainer):
    """Fixture to provide the Keyvault instance."""
    return container.keyvault()


@pytest.fixture()
def state_machine(container: ApplicationContainer, robot):
    """Fixture to provide the StateMachine instance."""
    return StateMachine(
        events=container.events(),
        shared_state=container.shared_state(),
        robot=robot,
        mqtt_publisher=container.mqtt_client(),
        task_selector=container.task_selector(),
    )


@pytest.fixture()
def idle_state(state_machine):
    """Fixture to provide the Idle state."""
    return Idle(state_machine)


@pytest.fixture()
def monitor(state_machine):
    """Fixture to provide the Monitor state."""
    return Monitor(state_machine=state_machine)


@pytest.fixture()
def request_handler(container: ApplicationContainer):
    """Fixture to provide the RequestHandler instance."""
    return container.request_handler()


@pytest.fixture()
def local_planner(container: ApplicationContainer):
    """Fixture to provide the LocalPlanner instance."""
    return container.scheduling_utilities().mission_planner


@pytest.fixture()
def robot():
    """Fixture to provide a mock robot instance."""
    return MockRobot()


@pytest.fixture()
def scheduling_utilities(container: ApplicationContainer):
    """Fixture to provide the SchedulingUtilities instance."""
    return container.scheduling_utilities()


@pytest.fixture()
def mission_reader(container: ApplicationContainer):
    """Fixture to provide the LocalPlanner instance."""
    return container.scheduling_utilities().mission_planner


# @pytest.fixture
# def uploader(container: ApplicationContainer) -> Uploader:
#     uploader: Uploader = Uploader(
#         events=container.events(),
#         storage_handlers=container.storage_handlers(),
#         mqtt_publisher=container.mqtt_client(),
#     )
#     container.uploader.override(uploader)

#     # The thread is deliberately started but not joined so that it runs in the
#     # background and stops when the test ends
#     thread = Thread(target=uploader.run, daemon=True)
#     thread.start()

#     return uploader


@pytest.fixture
def state_machine_thread(container: ApplicationContainer) -> StateMachineThread:
    return StateMachineThread(container)


@pytest.fixture
def uploader_thread(container: ApplicationContainer) -> UploaderThread:
    return UploaderThread(container=container)


@pytest.fixture
def robot_service_thread(container: ApplicationContainer):
    robot_service_thread: RobotServiceThread = RobotServiceThread(container=container)
    yield robot_service_thread
    robot_service_thread.teardown()


# @pytest.fixture()
# def turtlebot_container(container: ApplicationContainer) -> ApplicationContainer:
#     container.config.from_dict(
#         {
#             "ROBOT_PACKAGE": "isar_turtlebot",
#             "LOCAL_STORAGE_PATH": "./tests/results",
#             "PREDEFINED_MISSIONS_FOLDER": "./tests/integration/turtlebot/config/missions",
#             "MAPS_FOLDER": "tests/integration/turtlebot/config/maps",
#             "DEFAULT_MAP": "turtleworld",
#         }
#     )
#     # TODO FIX
#     return container


# @pytest.fixture()
# def state_machine_thread(turtlebot_container) -> StateMachineThread:
#     return StateMachineThread(turtlebot_container)


# @pytest.fixture()
# def uploader_thread(turtlebot_container) -> UploaderThread:
#     return UploaderThread(turtlebot_container)


@pytest.fixture(autouse=True)
def run_before_and_after_tests() -> None:  # type: ignore
    results_folder: Path = Path("tests/results")
    yield

    print("Removing temporary results folder for testing")
    if results_folder.exists():
        shutil.rmtree(results_folder)
    print("Cleanup finished")
