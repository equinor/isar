from collections import deque
from http import HTTPStatus

import pytest
import sqlalchemy
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlalchemy.orm import Session

from isar.config.settings import settings
from isar.services.service_connections.persistent_memory import (
    PersistentRobotState,
    RobotStartupMode,
    change_persistent_robot_state_with_connection_string,
    read_persistent_robot_state,
    read_persistent_robot_state_with_connection_string,
)
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import MissionStatus, RobotStatus
from tests.test_mocks.mission_definition import DummyMissionDefinition
from tests.test_mocks.robot_interface import StubRobot
from tests.test_mocks.state_machine_mocks import (
    RobotServiceThreadMock,
    StateMachineThreadMock,
)
from tests.wait import wait_until


@pytest.fixture
def persisted_robot(setup_db_connection_string: str) -> str:
    engine = sqlalchemy.create_engine(setup_db_connection_string)
    with Session(engine) as session:
        session.add(
            PersistentRobotState(
                robot_id="0a0", robot_startup_mode=RobotStartupMode.Lockdown
            )
        )
        session.commit()
    engine.dispose()
    return setup_db_connection_string


def test_reads_persisted_mode(persisted_robot: str) -> None:
    mode = read_persistent_robot_state_with_connection_string(persisted_robot, "0a0")

    assert mode == RobotStartupMode.Lockdown


@pytest.mark.parametrize(
    "mode", [RobotStartupMode.Normal, RobotStartupMode.Maintenance]
)
def test_changes_persisted_mode(persisted_robot: str, mode: RobotStartupMode) -> None:
    change_persistent_robot_state_with_connection_string(persisted_robot, "0a0", mode)

    assert (
        read_persistent_robot_state_with_connection_string(persisted_robot, "0a0")
        == mode
    )


@pytest.fixture
def running_mission(
    state_machine_thread_with_db: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
    scheduling_utilities: SchedulingUtilities,
    mocker: MockerFixture,
) -> StateMachineThreadMock:
    mocker.patch.object(StubRobot, "robot_status", return_value=RobotStatus.Home)
    mocker.patch.object(
        StubRobot, "mission_status", return_value=MissionStatus.InProgress
    )
    state_machine_thread_with_db.start()
    robot_service_thread.start()
    wait_until(
        lambda: state_machine_thread_with_db.state_machine.events.robot_async_events.robot_status_update.check()
        == RobotStatus.Home,
        timeout=10.0,
    )
    scheduling_utilities.release_maintenance_mode()
    wait_until(
        lambda: state_machine_thread_with_db.state_machine.current_state.name
        == States.Home
    )
    scheduling_utilities.start_mission(
        DummyMissionDefinition.default_mission.model_copy(deep=True)
    )
    wait_until(
        lambda: state_machine_thread_with_db.state_machine.current_state.name
        == States.Monitor
    )
    return state_machine_thread_with_db


@pytest.mark.parametrize(
    ("endpoint", "mode", "terminal_transitions"),
    [
        pytest.param(
            "lockdown",
            RobotStartupMode.Lockdown,
            [States.StoppingGoToLockdown, States.GoingToLockdown, States.Lockdown],
            id="lockdown",
        ),
        pytest.param(
            "maintenance-mode",
            RobotStartupMode.Maintenance,
            [States.StoppingDueToMaintenance, States.Maintenance],
            id="maintenance",
        ),
    ],
)
def test_mode_change_stops_mission_and_persists_mode(
    running_mission: StateMachineThreadMock,
    client: TestClient,
    mocker: MockerFixture,
    endpoint: str,
    mode: RobotStartupMode,
    terminal_transitions: list[States],
) -> None:
    expected_transitions = deque(
        [States.Maintenance, States.UnknownStatus, States.Home, States.Monitor]
        + terminal_transitions
    )

    response = client.post(url=f"/schedule/{endpoint}")
    mocker.patch.object(
        StubRobot, "mission_status", return_value=MissionStatus.Successful
    )

    assert response.status_code == HTTPStatus.OK
    wait_until(
        lambda: running_mission.state_machine.transitions_list == expected_transitions,
        timeout=10.0,
    )
    assert read_persistent_robot_state(settings.ISAR_ID) == mode


def test_release_maintenance_mode(
    state_machine_thread_with_db: StateMachineThreadMock,
    client: TestClient,
    robot_service_thread: RobotServiceThreadMock,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(StubRobot, "robot_status", return_value=RobotStatus.Home)
    state_machine_thread_with_db.start()
    robot_service_thread.start()
    wait_until(
        lambda: state_machine_thread_with_db.state_machine.events.robot_async_events.robot_status_update.check()
        == RobotStatus.Home,
        timeout=10.0,
    )
    expected_transitions = deque(
        [States.Maintenance, States.UnknownStatus, States.Home]
    )

    response = client.post(url="/schedule/release-maintenance-mode")

    assert response.status_code == HTTPStatus.OK
    wait_until(
        lambda: state_machine_thread_with_db.state_machine.transitions_list
        == expected_transitions
    )
    assert read_persistent_robot_state(settings.ISAR_ID) == RobotStartupMode.Normal
