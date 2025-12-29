import shutil
from pathlib import Path

import pytest
import sqlalchemy
from dependency_injector.wiring import providers
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from testcontainers.mysql import MySqlContainer

from isar.apis.security.authentication import Authenticator
from isar.config.settings import settings
from isar.eventhandlers.eventhandler import State
from isar.models.events import Events
from isar.modules import ApplicationContainer
from isar.robot.robot import Robot
from isar.robot.robot_battery import RobotBatteryThread
from isar.robot.robot_monitor_mission import RobotMonitorMissionThread
from isar.robot.robot_pause_mission import RobotPauseMissionThread
from isar.robot.robot_resume_mission import RobotResumeMissionThread
from isar.robot.robot_start_mission import RobotStartMissionThread
from isar.robot.robot_status import RobotStatusThread
from isar.robot.robot_stop_mission import RobotStopMissionThread
from isar.robot.robot_upload_inspection import RobotUploadInspectionThread
from isar.services.service_connections.persistent_memory import Base
from isar.state_machine.state_machine import StateMachine
from isar.storage.uploader import Uploader
from tests.test_mocks.blob_storage import StorageFake
from tests.test_mocks.robot_interface import StubRobot
from tests.test_mocks.state_machine_mocks import (
    RobotServiceThreadMock,
    StateMachineThreadMock,
    UploaderThreadMock,
)


@pytest.fixture(autouse=True)
def setup_test_environment():
    settings.PERSISTENT_STORAGE_CONNECTION_STRING = ""


@pytest.fixture()
def container():
    """Fixture to provide the dependency-injector container without auth."""
    container = ApplicationContainer()
    container.events.override(providers.Singleton(Events))
    container.storage_handlers.override(
        providers.List(providers.Singleton(StorageFake))
    )
    container.robot_interface.override(providers.Singleton(StubRobot))
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
    )


@pytest.fixture()
def sync_state_machine(container: ApplicationContainer, robot, mocker: MockerFixture):
    """Fixture to provide the StateMachine instance without running the state loops."""
    mocker.patch.object(State, "run", return_value=lambda: None)
    return StateMachine(
        events=container.events(),
        shared_state=container.shared_state(),
        robot=robot,
        mqtt_publisher=container.mqtt_client(),
    )


@pytest.fixture()
def request_handler(container: ApplicationContainer):
    """Fixture to provide the RequestHandler instance."""
    return container.request_handler()


@pytest.fixture()
def robot():
    """Fixture to provide a mock robot instance."""
    return StubRobot()


@pytest.fixture()
def scheduling_utilities(container: ApplicationContainer):
    """Fixture to provide the SchedulingUtilities instance."""
    return container.scheduling_utilities()


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
        mqtt_publisher=container.mqtt_client(),
    )

    robot_service_thread: RobotServiceThreadMock = RobotServiceThreadMock(
        robot_service=robot_service
    )
    yield robot_service_thread
    robot_service_thread.join()


@pytest.fixture
def mocked_robot_service(container: ApplicationContainer, mocker):
    robot_service: Robot = Robot(
        events=container.events(),
        robot=container.robot_interface(),
        shared_state=container.shared_state(),
        mqtt_publisher=container.mqtt_client(),
    )

    mocker.patch.object(RobotStartMissionThread, "run", return_value=lambda: None)
    mocker.patch.object(RobotBatteryThread, "run", return_value=lambda: None)
    mocker.patch.object(RobotStatusThread, "run", return_value=lambda: None)
    mocker.patch.object(RobotMonitorMissionThread, "run", return_value=lambda: None)
    mocker.patch.object(RobotStopMissionThread, "run", return_value=lambda: None)
    mocker.patch.object(RobotPauseMissionThread, "run", return_value=lambda: None)
    mocker.patch.object(RobotResumeMissionThread, "run", return_value=lambda: None)
    mocker.patch.object(RobotUploadInspectionThread, "run", return_value=lambda: None)

    mocker.patch.object(RobotStartMissionThread, "join", return_value=lambda: None)
    mocker.patch.object(RobotBatteryThread, "join", return_value=lambda: None)
    mocker.patch.object(RobotStatusThread, "join", return_value=lambda: None)
    mocker.patch.object(RobotMonitorMissionThread, "join", return_value=lambda: None)
    mocker.patch.object(RobotStopMissionThread, "join", return_value=lambda: None)
    mocker.patch.object(RobotPauseMissionThread, "join", return_value=lambda: None)
    mocker.patch.object(RobotResumeMissionThread, "join", return_value=lambda: None)
    mocker.patch.object(RobotUploadInspectionThread, "join", return_value=lambda: None)

    return robot_service


@pytest.fixture(autouse=True)
def run_before_and_after_tests() -> None:  # type: ignore
    results_folder: Path = Path("tests/results")
    yield

    print("Removing temporary results folder for testing")
    if results_folder.exists():
        shutil.rmtree(results_folder)
    print("Cleanup finished")


@pytest.fixture()
def setup_db_connection_string():
    with MySqlContainer("mysql:9.4.0", dialect="pymysql") as mysql:
        connection_url = mysql.get_connection_url()
        settings.PERSISTENT_STORAGE_CONNECTION_STRING = connection_url

        engine = sqlalchemy.create_engine(connection_url)
        Base.metadata.create_all(engine)

        yield
