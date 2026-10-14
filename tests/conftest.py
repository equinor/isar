# import warnings
# # This removes the deprecation warning in testcontainers that is not our fault
# warnings.filterwarnings("ignore", category=DeprecationWarning, module="testcontainers")

import logging
import shutil
from collections.abc import Callable, Generator
from pathlib import Path
from threading import Thread
from typing import Any

import pytest
import sqlalchemy
from dependency_injector.wiring import providers
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from testcontainers.mysql import MySqlContainer

from isar.apis.security.authentication import Authenticator
from isar.config.settings import settings
from isar.models.events import Events
from isar.modules import ApplicationContainer
from isar.robot.function_thread import FunctionThread
from isar.robot.robot_battery import RobotBatteryThread
from isar.robot.robot_inspection_service import RobotInspectionService
from isar.robot.robot_service import RobotService
from isar.robot.robot_status import RobotStatusThread
from isar.services.service_connections.persistent_memory import Base
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.state import State, StateDef
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.await_next_mission import AwaitNextMission
from isar.state_machine.states.going_to_lockdown import GoingToLockdown
from isar.state_machine.states.going_to_lockdown_with_mission import (
    GoingToLockdownWithMission,
)
from isar.state_machine.states.going_to_recharging import GoingToRecharging
from isar.state_machine.states.going_to_recharging_with_mission import (
    GoingToRechargingWithMission,
)
from isar.state_machine.states.home import Home
from isar.state_machine.states.intervention_needed import InterventionNeeded
from isar.state_machine.states.lockdown import Lockdown
from isar.state_machine.states.lockdown_with_mission import LockdownWithMission
from isar.state_machine.states.maintenance import Maintenance
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states.offline import Offline
from isar.state_machine.states.paused import Paused
from isar.state_machine.states.pausing import Pausing
from isar.state_machine.states.pausing_return_home import PausingReturnHome
from isar.state_machine.states.recharging import Recharging
from isar.state_machine.states.recharging_with_mission import RechargingWithMission
from isar.state_machine.states.resuming import Resuming
from isar.state_machine.states.resuming_return_home import ResumingReturnHome
from isar.state_machine.states.return_home_paused import ReturnHomePaused
from isar.state_machine.states.returning_home import ReturningHome
from isar.state_machine.states.stopping import Stopping
from isar.state_machine.states.stopping_due_to_maintenance import (
    StoppingDueToMaintenance,
)
from isar.state_machine.states.stopping_go_to_lockdown import StoppingGoToLockdown
from isar.state_machine.states.stopping_go_to_recharge import StoppingGoToRecharge
from isar.state_machine.states.stopping_paused_mission import StoppingPausedMission
from isar.state_machine.states.stopping_paused_return_home import (
    StoppingPausedReturnHome,
)
from isar.state_machine.states.stopping_return_home import StoppingReturnHome
from isar.state_machine.states.stopping_unknown_mission import StoppingUnknownMission
from isar.state_machine.states.unknown_status import UnknownStatus
from isar.state_machine.states_enum import States
from isar.storage.storage_interface import StorageInterface
from isar.storage.uploader import Uploader
from robot_interface.models.mission.mission import Mission
from tests.test_mocks.blob_storage import StorageFake
from tests.test_mocks.robot_interface import StubRobot
from tests.test_mocks.state_machine_mocks import (
    RobotServiceThreadMock,
    StateMachineThreadMock,
)


@pytest.fixture(autouse=True)
def setup_test_environment() -> None:
    logger_names = [
        "main",
        "api",
        "state_machine",
        "robot",
        "mqtt_client",
        "uploader",
        "fastapi_azure_auth",
    ]
    loggers = [logging.getLogger(name) for name in logger_names]
    for logger in loggers:
        logger.propagate = False  # Turn off logging in the command line for testing


@pytest.fixture()
def container() -> ApplicationContainer:
    """Fixture to provide the dependency-injector container without auth."""
    container = ApplicationContainer()

    container.events.override(providers.Singleton(Events))
    container.mqtt_queue.override(
        providers.Object(container.events.provided.mqtt_queue)
    )
    container.storage_handlers.override(
        providers.List(providers.Singleton(StorageFake))
    )
    container.robot_interface.override(providers.Singleton(StubRobot))
    container.uploader.override(
        providers.Singleton(
            Uploader,
            container.storage_handlers(),
            container.mqtt_queue(),
        )
    )
    container.robot.override(
        providers.Singleton(
            RobotService,
            events=container.events(),
            robot=container.robot_interface(),
            mqtt_queue=container.mqtt_queue(),
        )
    )
    container.inspection_service.override(
        providers.Singleton(
            RobotInspectionService,
            events=container.events(),
            robot=container.robot_interface(),
            mqtt_queue=container.mqtt_queue(),
        )
    )
    container.state_machine.override(
        providers.Singleton(
            StateMachine,
            events=container.events,
            mqtt_queue=container.mqtt_queue(),
        )
    )
    return container


@pytest.fixture()
def app(container: ApplicationContainer) -> FastAPI:
    """Fixture to provide the FastAPI app."""
    container.authenticator.override(
        providers.Singleton(Authenticator, authentication_enabled=False)
    )

    app = container.api().get_app()
    return app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    """Fixture to provide a test client for the FastAPI app."""
    client = TestClient(app)
    return client


@pytest.fixture()
def client_auth(container: ApplicationContainer) -> TestClient:
    """Fixture to provide a test client for the FastAPI app with auth."""
    container.authenticator.override(
        providers.Singleton(Authenticator, authentication_enabled=True)
    )

    app = container.api().get_app()
    client = TestClient(app)
    return client


@pytest.fixture()
def access_token() -> str:
    """Fixture to provide a dummy access token."""
    return "DummyToken"


@pytest.fixture()
def events(container: ApplicationContainer) -> Events:
    """Fixture to provide a test with the global event queues."""
    return container.events()


@pytest.fixture()
def storage_handlers(container: ApplicationContainer) -> list[StorageInterface]:
    return container.storage_handlers()


@pytest.fixture()
def state_machine(container: ApplicationContainer) -> StateMachine:
    """Fixture to provide the StateMachine instance."""
    return container.state_machine()


@pytest.fixture()
def uploader(container: ApplicationContainer) -> Uploader:
    """Fixture to provide a mock robot instance."""
    return container.uploader()


@pytest.fixture()
def scheduling_utilities(
    container: ApplicationContainer,
) -> SchedulingUtilities:
    """Fixture to provide the SchedulingUtilities instance."""
    return SchedulingUtilities(
        events=container.events(),
        state_machine=container.state_machine(),
    )


@pytest.fixture()
def state_machine_thread(
    container: ApplicationContainer,
    mocker: MockerFixture,
) -> Generator[StateMachineThreadMock]:
    mocker.patch.object(settings, "USE_DB", False)
    state_machine_thread: StateMachineThreadMock = StateMachineThreadMock(
        container=container,
    )
    yield state_machine_thread
    state_machine_thread.join()


@pytest.fixture()
def state_machine_thread_with_db(
    setup_db_connection_string: str,
    container: ApplicationContainer,
    mocker: MockerFixture,
) -> Generator[StateMachineThreadMock]:
    mocker.patch.object(settings, "USE_DB", True)
    # read_persistent_robot_state
    mocker.patch(
        "isar.services.service_connections.persistent_memory.get_db_connection_string",
        return_value=setup_db_connection_string,
    )
    state_machine_thread: StateMachineThreadMock = StateMachineThreadMock(
        container=container,
    )
    yield state_machine_thread
    state_machine_thread.join()


@pytest.fixture()
def robot_service_thread(
    container: ApplicationContainer,
) -> Generator[RobotServiceThreadMock]:
    robot_service: RobotService = RobotService(
        events=container.events(),
        robot=container.robot_interface(),
        mqtt_queue=container.mqtt_queue(),
    )

    robot_service_thread: RobotServiceThreadMock = RobotServiceThreadMock(
        robot_service=robot_service
    )
    yield robot_service_thread
    robot_service_thread.join()


@pytest.fixture()
def robot_inspection_service_thread(
    container: ApplicationContainer,
) -> Generator[Thread]:
    robot_inspection_service: RobotInspectionService = RobotInspectionService(
        events=container.events(),
        robot=container.robot_interface(),
        uploader=container.uploader(),
    )

    robot_inspection_service_thread: Thread = Thread(
        target=robot_inspection_service.run
    )
    yield robot_inspection_service_thread
    robot_inspection_service.stop()
    robot_inspection_service_thread.join()


@pytest.fixture()
def mocked_robot_service(
    container: ApplicationContainer, mocker: MockerFixture
) -> RobotService:
    robot_service: RobotService = RobotService(
        events=container.events(),
        robot=container.robot_interface(),
        mqtt_queue=container.mqtt_queue(),
    )

    mocker.patch.object(RobotBatteryThread, "run", return_value=lambda: None)
    mocker.patch.object(RobotStatusThread, "run", return_value=lambda: None)
    mocker.patch.object(FunctionThread, "run", return_value=lambda: None)

    mocker.patch.object(RobotBatteryThread, "join", return_value=lambda: None)
    mocker.patch.object(RobotStatusThread, "join", return_value=lambda: None)
    mocker.patch.object(FunctionThread, "join", return_value=lambda: None)

    return robot_service


@pytest.fixture()
def all_state_functions(
    container: ApplicationContainer,
) -> dict[States, tuple[Callable[[Any], StateDef], tuple]]:
    events = container.events()

    mission = Mission(id="", tasks=[], name="")
    states = {
        States.Monitor: (Monitor, (events, "")),
        States.ReturningHome: (ReturningHome, (events,)),
        States.Stopping: (Stopping, (events, "")),
        States.StoppingUnknownMission: (StoppingUnknownMission, (events,)),
        States.StoppingReturnHome: (StoppingReturnHome, (events, mission)),
        States.Paused: (Paused, (events, "")),
        States.Pausing: (Pausing, (events, "")),
        States.Resuming: (Resuming, (events, "")),
        States.PausingReturnHome: (PausingReturnHome, (events,)),
        States.ResumingReturnHome: (ResumingReturnHome, (events,)),
        States.ReturnHomePaused: (ReturnHomePaused, (events,)),
        States.AwaitNextMission: (AwaitNextMission, (events,)),
        States.Home: (Home, (events,)),
        States.Offline: (Offline, (events,)),
        States.UnknownStatus: (UnknownStatus, (events,)),
        States.InterventionNeeded: (InterventionNeeded, (events,)),
        States.Recharging: (Recharging, (events,)),
        States.RechargingWithMission: (RechargingWithMission, (events, mission)),
        States.StoppingGoToLockdown: (StoppingGoToLockdown, (events, "")),
        States.GoingToLockdown: (GoingToLockdown, (events,)),
        States.Lockdown: (Lockdown, (events,)),
        States.GoingToRecharging: (GoingToRecharging, (events,)),
        States.GoingToRechargingWithMission: (
            GoingToRechargingWithMission,
            (events, mission),
        ),
        States.StoppingGoToRecharge: (StoppingGoToRecharge, (events,)),
        States.Maintenance: (Maintenance, (events,)),
        States.StoppingDueToMaintenance: (StoppingDueToMaintenance, (events,)),
        States.StoppingPausedMission: (StoppingPausedMission, (events, "")),
        States.StoppingPausedReturnHome: (StoppingPausedReturnHome, (events, mission)),
        States.GoingToLockdownWithMission: (
            GoingToLockdownWithMission,
            (events, mission),
        ),
        States.LockdownWithMission: (LockdownWithMission, (events, mission)),
    }

    assert len(States) == len(
        states.items()
    ), "Remember to include all states in this list"

    # Reason for ignoring the type is that Callables are incorrectly interpreted as 'function'
    # See https://github.com/python/mypy/issues/17478 for more details
    return states  # type: ignore


@pytest.fixture()
def all_states_dict(
    all_state_functions: dict[States, tuple[Callable[[Any], StateDef], tuple]],
) -> dict[States, State]:
    all_states_dict = {
        state_name: State(mapping[0](*mapping[1]))
        for state_name, mapping in all_state_functions.items()
    }

    assert len(States) == len(
        all_states_dict.items()
    ), "Remember to include all states in this list"
    return all_states_dict


@pytest.fixture(autouse=True)
def run_before_and_after_tests(container: ApplicationContainer) -> Generator[None]:
    results_folder: Path = Path("tests/results")

    yield

    container.events.reset()
    container.mqtt_queue.override(
        providers.Object(container.events.provides().mqtt_queue)
    )

    print("Removing temporary results folder for testing")
    if results_folder.exists():
        shutil.rmtree(results_folder)
    print("Cleanup finished")


@pytest.fixture()
def setup_db_connection_string() -> Generator[str]:
    with MySqlContainer("mysql:9.4.0", dialect="pymysql") as mysql:
        connection_url = mysql.get_connection_url()

        engine = sqlalchemy.create_engine(connection_url)
        Base.metadata.create_all(engine)

        yield connection_url
