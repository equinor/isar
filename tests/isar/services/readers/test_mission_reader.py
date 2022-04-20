from pathlib import Path

import pytest
from alitra import Frame, Orientation, Pose, Position

from isar.config.settings import settings
from isar.mission_planner.mission_planner_interface import MissionPlannerError
from isar.models.mission import Mission
from robot_interface.models.mission import TakeThermalImage
from robot_interface.models.mission.task import DriveToPose, TakeImage, Task


@pytest.mark.parametrize(
    "mission_path",
    [
        Path("./tests/test_data/test_mission_working_notasks.json"),
        Path("./tests/test_data/test_mission_working.json"),
    ],
)
def test_get_mission(mission_reader, mission_path):
    output: Mission = mission_reader.read_mission_from_file(mission_path)
    assert isinstance(output, Mission)


def test_read_mission_from_file(mission_reader):
    expected_task_1 = DriveToPose(
        pose=Pose(
            position=Position(-2, -2, 0, Frame("asset")),
            orientation=Orientation(0, 0, 0.4794255, 0.8775826, Frame("asset")),
            frame=Frame("asset"),
        )
    )
    expected_task_2 = DriveToPose(
        pose=Pose(
            position=Position(-2, 2, 0, Frame("asset")),
            orientation=Orientation(0, 0, 0.4794255, 0.8775826, Frame("asset")),
            frame=Frame("asset"),
        )
    )
    expected_task_3 = TakeImage(target=Position(2, 2, 0, Frame("robot")))
    expected_task_4 = DriveToPose(
        pose=Pose(
            position=Position(2, 2, 0, Frame("asset")),
            orientation=Orientation(0, 0, 0.4794255, 0.8775826, Frame("asset")),
            frame=Frame("asset"),
        )
    )
    expected_task_5 = TakeImage(target=Position(2, 2, 0, Frame("robot")), depends_on=0)
    expected_task_6 = DriveToPose(
        pose=Pose(
            position=Position(0, 0, 0, Frame("asset")),
            orientation=Orientation(0, 0, 0.4794255, 0.8775826, Frame("asset")),
            frame=Frame("asset"),
        ),
        depends_on=[1, 2],
    )
    expected_tasks = [
        expected_task_1,
        expected_task_2,
        expected_task_3,
        expected_task_4,
        expected_task_5,
        expected_task_6,
    ]
    expected_mission: Mission = Mission(tasks=expected_tasks)
    mission: Mission = mission_reader.read_mission_from_file(
        Path("./tests/test_data/test_mission_working.json")
    )
    assert (
        expected_mission.metadata.coordinate_reference_system
        == mission.metadata.coordinate_reference_system
    )
    assert (
        expected_mission.metadata.vertical_reference_system
        == mission.metadata.vertical_reference_system
    )
    assert (
        expected_mission.metadata.data_classification
        == mission.metadata.data_classification
    )
    for expected_task, task in zip(expected_tasks, mission.tasks):
        if isinstance(expected_task, DriveToPose) and isinstance(task, DriveToPose):
            assert expected_task.pose == task.pose
        if isinstance(expected_task, TakeImage) and isinstance(task, TakeImage):
            assert expected_task.target == task.target


@pytest.mark.parametrize(
    "mission_path",
    [
        (Path("./tests/test_data/no_file.json")),
        (Path("./tests/test_data/test_mission_not_working.json")),
    ],
)
def test_get_invalid_mission(mission_reader, mission_path):
    with pytest.raises(Exception):
        mission_reader.read_mission_from_file(mission_path)


def test_get_mission_by_id(mission_reader):
    output = mission_reader.get_mission(1)
    assert isinstance(output, Mission)


def test_get_mission_by_invalid_id(mission_reader):
    with pytest.raises(MissionPlannerError):
        mission_reader.get_mission(12345)


def test_valid_predefined_missions_files(mission_reader):
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


def test_thermal_image_task(mission_reader):
    mission_path: Path = Path("./tests/test_data/test_thermal_image_mission.json")
    output: Mission = mission_reader.read_mission_from_file(mission_path)

    task: Task = output.tasks[0]

    assert isinstance(task, TakeThermalImage)
    assert hasattr(task, "target")
    assert task.type == "take_thermal_image"
    assert hasattr(task, "id")
    assert hasattr(task, "tag_id")


def test_mission_dependencies(mission_reader):
    mission_path = Path("./tests/test_data/test_mission_working.json")
    mission: Mission = mission_reader.read_mission_from_file(mission_path)
    mission.set_task_dependencies()

    task_dependencies = [
        None,
        None,
        [mission.tasks[1].id],
        None,
        [mission.tasks[0].id],
        [mission.tasks[1].id, mission.tasks[2].id],
    ]

    for task, dependencies in zip(mission.tasks, task_dependencies):
        assert task.depends_on == dependencies
