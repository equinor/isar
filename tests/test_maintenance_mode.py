from http import HTTPStatus
import time

from pytest import MonkeyPatch
import pytest
import sqlalchemy
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from testcontainers.mysql import MySqlContainer

from isar.services.service_connections.persistent_memory import Base, PersistentRobotState, change_persistent_robot_state_is_maintenance_mode, read_persistent_robot_state_is_maintenance_mode
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import MissionStatus
from tests.isar.state_machine.test_state_machine import (
    RobotServiceThreadMock,
    StateMachineThreadMock,
)
from isar.config.settings import settings
from tests.test_double.robot_interface import StubRobot


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

        is_maintenance_mode = read_persistent_robot_state_is_maintenance_mode(connection_url, "0a0")
        assert is_maintenance_mode
        change_persistent_robot_state_is_maintenance_mode(connection_url, "0a0", value=False)
        is_maintenance_mode = read_persistent_robot_state_is_maintenance_mode(connection_url, "0a0")
        assert not is_maintenance_mode

@pytest.fixture()
def setup_db_connection_string():
     with MySqlContainer("mysql:9.4.0", dialect="pymysql") as mysql:
        connection_url = mysql.get_connection_url()
        # monkeypatch.setenv('PERSISTENT_STORAGE_CONNECTION_STRING', connection_url)
        settings.PERSISTENT_STORAGE_CONNECTION_STRING = connection_url

        engine = sqlalchemy.create_engine(connection_url)
        Base.metadata.create_all(engine)
        
        yield 

def test_maintenance_mode(
    setup_db_connection_string, # The order of the fixtures is important
    client: TestClient,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
    # monkeypatch: MonkeyPatch # This is a default fixture from pytest for changing attributes and environment variables for this test only. 
    mocker
) -> None:
        # Now running ISAR should put it into maintenance mode
        state_machine_thread.start()
        robot_service_thread.start()

        assert state_machine_thread.state_machine.current_state == States.Maintenance

        # The robot should ahve started in maintenance mode since the robot id is not found in the database. 
        response = client.post(url="/schedule/start-mission/1")
        assert response.status_code == HTTPStatus.CONFLICT

        response = client.post(url="/schedule/release-maintenance-mode")
        assert response.status_code == HTTPStatus.OK
        assert state_machine_thread.state_machine.current_state != States.Maintenance

        t_start = time.time()
        while state_machine_thread.state_machine.current_state == States.UnknownStatus:
             if time.time() - t_start > 10:
                  raise Exception("Robot could not leave unknown state after releasing maintenance mode")
             time.sleep(0.5)

        # Find transitions list: state_machine_thread.state_machine.transitions_list
        mocker.patch.object(StubRobot, "mission_status", return_value=MissionStatus.InProgress) # The robot will not go to awaitng next mission after mission has started, it should remain in monitor. In order to test the "stop" functionality. 
        response = client.post(url="/schedule/start-mission/1")
        assert response.status_code == HTTPStatus.OK
        # assert "monitor" in state_machine_thread.state_machine.transitions_list

        assert state_machine_thread.state_machine.current_state == States.Monitor
        response = client.post(url="/schedule/maintenance-mode")
        assert response.status_code == HTTPStatus.OK

        response = client.post(url="/schedule/start-mission/1")
        assert response.status_code == HTTPStatus.CONFLICT
