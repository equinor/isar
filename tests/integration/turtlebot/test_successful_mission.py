import json
import time
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

import numpy as np
from alitra import Frame, Position
from fastapi import FastAPI
from starlette.testclient import TestClient

from isar.apis.api import API
from isar.state_machine.states_enum import States
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import ReturnToHome


def test_successful_mission(
    injector_turtlebot, state_machine_thread, uploader_thread, access_token
) -> None:
    integration_test_timeout: timedelta = timedelta(minutes=5)
    app: FastAPI = injector_turtlebot.get(API).get_app()
    client: TestClient = TestClient(app=app)

    _id: int = 2

    _ = client.post(
        f"schedule/start-mission?ID={_id}",
        headers={"Authorization": "Bearer {}".format(access_token)},
    )
    time.sleep(5)

    mission_id: str = state_machine_thread.state_machine.current_mission.id
    mission: Mission = deepcopy(state_machine_thread.state_machine.current_mission)

    start_time: datetime = datetime.now(timezone.utc)
    while state_machine_thread.state_machine.current_state != States.RobotStandingStill:
        if (datetime.now(timezone.utc) - start_time) > integration_test_timeout:
            raise TimeoutError
        time.sleep(5)

    mission_result_folder: Path = Path(f"tests/results/{mission_id}")

    drive_to_tasks: List[ReturnToHome] = [
        task for task in mission.tasks if isinstance(task, ReturnToHome)
    ]

    expected_positions: list = [task.pose for task in drive_to_tasks]

    paths = mission_result_folder.rglob("*.json")
    for path in paths:
        with open(path) as json_file:
            metadata = json.load(json_file)
        files_metadata: dict = metadata["data"][0]["files"][0]
        filename: str = files_metadata["file_name"]
        inspection_file: Path = mission_result_folder.joinpath(filename)

        actual_position: Position = Position(
            x=files_metadata["x"],
            y=files_metadata["y"],
            z=files_metadata["z"],
            frame=Frame("asset"),
        )

        close_to_expected_positions: List[bool] = []
        for expected_position in expected_positions:
            close_to_expected_positions.append(
                np.allclose(
                    actual_position.to_list(), expected_position.to_list(), atol=0.2
                )
            )

        assert any(close_to_expected_positions)
        assert inspection_file.exists()
    assert (
        len(list(mission_result_folder.glob("*"))) == 6
    )  # Expected two images, one thermal + three metadata files
