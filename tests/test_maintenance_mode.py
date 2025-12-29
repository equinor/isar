import time
from collections import deque
from http import HTTPStatus

import sqlalchemy
from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from testcontainers.mysql import MySqlContainer

from isar.services.service_connections.persistent_memory import (
    Base,
    PersistentRobotState,
    change_persistent_robot_state_is_maintenance_mode,
    read_persistent_robot_state_is_maintenance_mode,
)
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import MissionStatus, RobotStatus
from tests.test_mocks.mission_definition import DummyMissionDefinition
from tests.test_mocks.robot_interface import StubRobot
from tests.test_mocks.state_machine_mocks import (
    RobotServiceThreadMock,
    StateMachineThreadMock,
)


def test_persistent_storage_schema() -> None:
    with MySqlContainer("mysql:9.4.0", dialect="pymysql") as mysql:
        connection_url = mysql.get_connection_url()
        engine = sqlalchemy.create_engine(connection_url)
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            persistent_state = PersistentRobotState(
                robot_id="0a0", is_maintenance_mode=True
            )
            session.add_all([persistent_state])
            session.commit()

        is_maintenance_mode = read_persistent_robot_state_is_maintenance_mode(
            connection_url, "0a0"
        )
        assert is_maintenance_mode
        change_persistent_robot_state_is_maintenance_mode(
            connection_url, "0a0", value=False
        )
        is_maintenance_mode = read_persistent_robot_state_is_maintenance_mode(
            connection_url, "0a0"
        )
        assert not is_maintenance_mode


def test_maintenance_mode(
    setup_db_connection_string,  # The order of the fixtures is important
    client: TestClient,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
    mocker,
) -> None:
    # Now running ISAR should put it into maintenance mode
    state_machine_thread.start()
    robot_service_thread.start()

    assert state_machine_thread.state_machine.current_state.name == States.Maintenance

    # The robot should have started in maintenance mode since the robot id is not found in the database.
    response = client.post(
        url="/schedule/start-mission",
        json=jsonable_encoder(
            {
                "mission_definition": DummyMissionDefinition.dummy_start_mission_definition
            }
        ),
    )
    assert response.status_code == HTTPStatus.CONFLICT

    mocker.patch.object(StubRobot, "robot_status", return_value=RobotStatus.Home)
    t_start = time.time()
    while (
        state_machine_thread.state_machine.shared_state.robot_status.check()
        != RobotStatus.Home
    ):
        if time.time() - t_start > 10:
            raise Exception("Robot did not come Home within expected time")
        time.sleep(0.5)

    response = client.post(url="/schedule/release-maintenance-mode")
    assert response.status_code == HTTPStatus.OK
    assert state_machine_thread.state_machine.current_state.name == States.Home

    mocker.patch.object(
        StubRobot, "mission_status", return_value=MissionStatus.InProgress
    )  # The robot will not go to awaitng next mission after mission has started, it should remain in monitor. In order to test the "stop" functionality.
    response = client.post(
        url="/schedule/start-mission",
        json=jsonable_encoder(
            {
                "mission_definition": DummyMissionDefinition.dummy_start_mission_definition
            }
        ),
    )
    assert response.status_code == HTTPStatus.OK

    assert state_machine_thread.state_machine.current_state.name == States.Monitor
    response = client.post(url="/schedule/maintenance-mode")
    assert response.status_code == HTTPStatus.OK

    response = client.post(
        url="/schedule/start-mission",
        json=jsonable_encoder(
            {
                "mission_definition": DummyMissionDefinition.dummy_start_mission_definition
            }
        ),
    )
    assert response.status_code == HTTPStatus.CONFLICT

    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.Maintenance,
            States.Home,
            States.Monitor,
            States.StoppingDueToMaintenance,
            States.Maintenance,
        ]
    )
