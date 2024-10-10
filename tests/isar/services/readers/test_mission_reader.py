from pathlib import Path
from typing import List, Union

import pytest
from alitra import Frame, Orientation, Pose, Position

from isar.config.settings import settings
from isar.mission_planner.mission_planner_interface import MissionNotFoundError
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import (
    TASKS,
    ReturnToHome,
    TakeImage,
    TakeThermalImage,
)
from robot_interface.models.mission.task import Task


@pytest.mark.parametrize(
    "mission_path",
    [
        Path("./tests/test_data/test_mission_working_no_tasks.json"),
        Path("./tests/test_data/test_mission_working.json"),
    ],
)
def test_get_mission(mission_reader, mission_path) -> None:
    output: Mission = mission_reader.read_mission_from_file(mission_path)
    assert isinstance(output, Mission)


def test_read_mission_from_file(mission_reader) -> None:
    expected_robot_pose_1 = Pose(
        position=Position(-2, -2, 0, Frame("asset")),
        orientation=Orientation(0, 0, 0.4794255, 0.8775826, Frame("asset")),
        frame=Frame("asset"),
    )
    task_1: ReturnToHome = ReturnToHome(pose=expected_robot_pose_1)

    expected_robot_pose_2 = Pose(
        position=Position(-2, 2, 0, Frame("asset")),
        orientation=Orientation(0, 0, 0.4794255, 0.8775826, Frame("asset")),
        frame=Frame("asset"),
    )
    expected_inspection_target_1 = Position(2, 2, 0, Frame("robot"))
    task_2: TakeImage = TakeImage(
        target=expected_inspection_target_1, robot_pose=expected_robot_pose_2
    )

    expected_robot_pose_3 = Pose(
        position=Position(2, 2, 0, Frame("asset")),
        orientation=Orientation(0, 0, 0.4794255, 0.8775826, Frame("asset")),
        frame=Frame("asset"),
    )
    expected_inspection_target_2 = Position(2, 2, 0, Frame("robot"))
    task_3: TakeImage = TakeImage(
        target=expected_inspection_target_2, robot_pose=expected_robot_pose_3
    )

    expected_robot_pose_4 = Pose(
        position=Position(0, 0, 0, Frame("asset")),
        orientation=Orientation(0, 0, 0.4794255, 0.8775826, Frame("asset")),
        frame=Frame("asset"),
    )
    task_4: ReturnToHome = ReturnToHome(pose=expected_robot_pose_4)

    expected_tasks: List[TASKS] = [
        task_1,
        task_2,
        task_3,
        task_4,
    ]
    mission: Mission = mission_reader.read_mission_from_file(
        Path("./tests/test_data/test_mission_working.json")
    )

    for expected_task, task in zip(expected_tasks, mission.tasks):
        if isinstance(expected_task, ReturnToHome) and isinstance(task, ReturnToHome):
            assert expected_task.pose == task.pose
        if isinstance(expected_task, TakeImage) and isinstance(task, TakeImage):
            assert expected_task.target == task.target
            assert expected_task.robot_pose == task.robot_pose


@pytest.mark.parametrize(
    "mission_path",
    [
        (Path("./tests/test_data/no_file.json")),
        (Path("./tests/test_data/test_mission_not_working.json")),
    ],
)
def test_get_invalid_mission(mission_reader, mission_path) -> None:
    with pytest.raises(Exception):
        mission_reader.read_mission_from_file(mission_path)


def test_get_mission_by_id(mission_reader) -> None:
    output = mission_reader.get_mission("1")
    assert isinstance(output, Mission)


def test_get_mission_by_invalid_id(mission_reader) -> None:
    with pytest.raises(MissionNotFoundError):
        mission_reader.get_mission("12345")


def test_valid_predefined_missions_files(mission_reader) -> None:
    # Checks that the predefined mission folder contains only valid missions!
    mission_list_dict = mission_reader.get_predefined_missions()
    predefined_mission_folder = Path(settings.PREDEFINED_MISSIONS_FOLDER)
    assert len(list(predefined_mission_folder.glob("*.json"))) == len(
        list(mission_list_dict)
    )
    for file in predefined_mission_folder.glob("*.json"):
        path_to_file = predefined_mission_folder.joinpath(file.name)
        mission: Mission = mission_reader.read_mission_from_file(path_to_file)
        assert mission is not None


def test_thermal_image_task(mission_reader) -> None:
    mission_path: Path = Path("./tests/test_data/test_thermal_image_mission.json")
    output: Mission = mission_reader.read_mission_from_file(mission_path)

    task = output.tasks[0]
    assert isinstance(task, TakeThermalImage)
    assert hasattr(task, "target")
    assert task.type == "take_thermal_image"
    assert hasattr(task, "id")
    assert hasattr(task, "tag_id")
