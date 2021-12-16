import shutil
import time
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import numpy as np
import pytest
from fastapi import FastAPI
from injector import Injector
from starlette.testclient import TestClient

from isar.apis.api import API
from isar.config import config
from isar.models.mission import Mission
from isar.modules import (
    APIModule,
    CoordinateModule,
    LocalPlannerModule,
    LocalStorageModule,
    QueuesModule,
    ReaderModule,
    RequestHandlerModule,
    RobotModule,
    ServiceModule,
    StateMachineModule,
    UtilitiesModule,
)
from isar.services.readers.base_reader import BaseReader
from isar.state_machine.states_enum import States
from robot_interface.models.geometry.frame import Frame
from robot_interface.models.geometry.position import Position
from robot_interface.models.mission import DriveToPose
from tests.isar.state_machine.test_state_machine import StateMachineThread
from tests.test_modules import MockNoAuthenticationModule


@pytest.fixture()
def injector_turtlebot():
    config.set("DEFAULT", "robot_package", "isar_turtlebot")
    config.set("DEFAULT", "local_storage_path", "./tests/results")
    config.set(
        "DEFAULT",
        "predefined_missions_folder",
        "./tests/integration/turtlebot/config/missions",
    )

    config.set("DEFAULT", "maps_folder", "tests/integration/turtlebot/config/maps")
    config.set("DEFAULT", "default_map", "turtleworld")

    return Injector(
        [
            APIModule,
            MockNoAuthenticationModule,
            CoordinateModule,
            QueuesModule,
            ReaderModule,
            RequestHandlerModule,
            RobotModule,
            ServiceModule,
            StateMachineModule,
            LocalPlannerModule,
            LocalStorageModule,
            UtilitiesModule,
        ]
    )


@pytest.fixture()
def state_machine_thread(injector_turtlebot) -> StateMachineThread:
    return StateMachineThread(injector=injector_turtlebot)


@pytest.fixture(autouse=True)
def run_before_and_after_tests():
    results_folder: Path = Path("tests/results")
    yield

    print("Removing temporary results folder for testing")
    if results_folder.exists():
        shutil.rmtree(results_folder)
    print("Cleanup finished")


def test_successful_mission(
    injector_turtlebot, state_machine_thread, access_token
) -> None:
    integration_test_timeout: timedelta = timedelta(minutes=5)
    app: FastAPI = injector_turtlebot.get(API).get_app()
    client: TestClient = TestClient(app=app)

    _id: int = 2

    response = client.post(
        f"schedule/start-mission?ID={_id}",
        headers={"Authorization": "Bearer {}".format(access_token)},
    )
    time.sleep(5)

    mission_id: str = state_machine_thread.state_machine.current_mission.id
    mission: Mission = deepcopy(state_machine_thread.state_machine.current_mission)

    start_time: datetime = datetime.utcnow()
    while state_machine_thread.state_machine.current_state != States.Idle:
        if (datetime.utcnow() - start_time) > integration_test_timeout:
            raise TimeoutError
        time.sleep(5)

    mission_result_folder: Path = Path(f"tests/results/{mission_id}")
    image_folder: Path = mission_result_folder.joinpath("sensor_data/image")
    image_navi_file: Path = image_folder.joinpath(f"{mission_id}_image_NAVI.json")

    thermal_folder: Path = mission_result_folder.joinpath("sensor_data/thermal")
    thermal_navi_file: Path = thermal_folder.joinpath(f"{mission_id}_thermal_NAVI.json")

    mission_metadata_file: Path = mission_result_folder.joinpath(
        f"{mission_id}_META.json"
    )

    image_navi: dict = BaseReader.read_json(image_navi_file)
    position_1: Position = Position.from_list(
        image_navi[0]["position"], frame=Frame.Asset
    )
    position_2: Position = Position.from_list(
        image_navi[1]["position"], frame=Frame.Asset
    )

    thermal_navi: dict = BaseReader.read_json(thermal_navi_file)
    position_3: Position = Position.from_list(
        thermal_navi[0]["position"], frame=Frame.Asset
    )

    mission_metadata: dict = BaseReader.read_json(mission_metadata_file)
    folder_locations: list = mission_metadata["data"]

    actual_positions: list = [position_1, position_2, position_3]
    drive_to_tasks: List[DriveToPose] = [
        task for task in mission.tasks if isinstance(task, DriveToPose)
    ]
    expected_positions: list = [task.pose.position for task in drive_to_tasks]

    assert image_navi_file.exists()
    assert thermal_navi_file.exists()
    assert mission_metadata_file.exists()

    assert len(list(image_folder.glob("*"))) == 3  # Expected two images + metadata
    assert len(list(thermal_folder.glob("*"))) == 2  # Expected one thermal + metadata
    assert len(folder_locations) == 2  # Folders for images and thermal images

    for actual, expected in zip(actual_positions, expected_positions):
        assert np.allclose(actual.to_list(), expected.to_list(), atol=0.2)
