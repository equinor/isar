import shutil
from pathlib import Path

import pytest
from dependency_injector.wiring import providers
from fastapi.testclient import TestClient

from isar.apis.security.authentication import Authenticator
from isar.config.settings import settings
from isar.modules import ApplicationContainer
from isar.robot.robot import Robot
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states.robot_standing_still import RobotStandingStill
from isar.storage.uploader import Uploader
from tests.isar.state_machine.test_state_machine import (
    RobotServiceThreadMock,
    StateMachineThreadMock,
    UploaderThreadMock,
)
from tests.mocks.blob_storage import StorageMock
from tests.mocks.mqtt_client import MqttClientMock
from tests.mocks.robot_interface import MockRobot

# Speed up tests
settings.FSM_SLEEP_TIME = 0.001
settings.ROBOT_API_STATUS_POLL_INTERVAL = 0
settings.UPLOAD_FAILURE_MAX_WAIT = 3


@pytest.fixture()
def container():
    """Fixture to provide the dependency-injector container without auth."""
    container = ApplicationContainer()
    container.storage_handlers.override(
        providers.List(providers.Singleton(StorageMock))
    )
    container.mqtt_client.override(providers.Singleton(MqttClientMock))
    container.robot_interface.override(providers.Singleton(MockRobot))
    container.uploader.override(
        providers.Singleton(
            Uploader,
            container.events(),
            container.storage_handlers(),
            container.mqtt_client(),
        )
    )
    container.robot.override(
        providers.Singleton(
            Robot,
            events=container.events(),
            robot=container.robot_interface(),
            shared_state=container.shared_state(),
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
def robot_standing_still_state(state_machine):
    """Fixture to provide the Robot Standing Still state."""
    return RobotStandingStill(state_machine)


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


@pytest.fixture
def state_machine_thread(container: ApplicationContainer):
    state_machine_thread: StateMachineThreadMock = StateMachineThreadMock(
        container=container,
    )
    yield state_machine_thread
    state_machine_thread.join()


@pytest.fixture
def uploader_thread(container: ApplicationContainer):
    uploader_thread: UploaderThreadMock = UploaderThreadMock(container=container)
    yield uploader_thread
    uploader_thread.join()


@pytest.fixture
def robot_service_thread(container: ApplicationContainer):
    robot_service: Robot = Robot(
        events=container.events(),
        robot=container.robot_interface(),
        shared_state=container.shared_state(),
    )

    robot_service_thread: RobotServiceThreadMock = RobotServiceThreadMock(
        robot_service=robot_service
    )
    yield robot_service_thread
    robot_service_thread.join()


@pytest.fixture(autouse=True)
def run_before_and_after_tests() -> None:  # type: ignore
    results_folder: Path = Path("tests/results")
    yield

    print("Removing temporary results folder for testing")
    if results_folder.exists():
        shutil.rmtree(results_folder)
    print("Cleanup finished")
