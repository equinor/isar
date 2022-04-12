from pathlib import Path

import pytest

from isar.config.settings import settings
from isar.mission_planner.mission_planner_interface import MissionPlannerError
from isar.models.mission import Mission
from robot_interface.models.mission import TakeThermalImage
from robot_interface.models.mission.task import Task


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
