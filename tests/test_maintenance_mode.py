from http import HTTPStatus

import sqlalchemy
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from testcontainers.mysql import MySqlContainer

from isar.services.service_connections.persistent_memory import Base, PersistentRobotState
from tests.isar.state_machine.test_state_machine import (
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

        with Session(engine) as session:
            statement = sqlalchemy.select(PersistentRobotState).where(
                PersistentRobotState.is_maintenance_mode
            )
            read_persistent_state = session.scalar(statement)

            assert read_persistent_state.robot_id == "0a0"


def test_maintenance_mode(
    client: TestClient,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
) -> None:
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

        # Now running ISAR should put it into maintenance mode
        state_machine_thread.start()
        robot_service_thread.start()

        schedule_start_mission_path = "/schedule/start-mission"
        response = client.post(url=f"{schedule_start_mission_path}/1")
        assert response.status_code == HTTPStatus.CONFLICT
