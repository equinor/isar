from pathlib import Path

import pytest

from isar.config import config
from isar.models.mission import Mission
from robot_interface.models.mission import TakeThermalImage
from robot_interface.models.mission.task import Task
from tests.utilities import Utilities


@pytest.mark.parametrize(
    "mission_path ,expected_output",
    [
        (
            Path("./tests/test_data/test_mission_working_notasks.json"),
            Mission,
        ),
        (Path("./tests/test_data/test_mission_working.json"), Mission),
    ],
)
def test_get_mission(mission_reader, mission_path, expected_output):
    output: Mission = mission_reader.read_mission_from_file(mission_path)
    assert Utilities.compare_two_arguments(output, expected_output)


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


@pytest.mark.parametrize(
    "mission_id ,expected_output",
    [(1, Mission)],
)
def test_get_mission_by_id(mission_reader, mission_id, expected_output):
    output = mission_reader.get_mission(mission_id)
    assert Utilities.compare_two_arguments(output, expected_output)


@pytest.mark.parametrize(
    "mission_id",
    [12345, None, config],
)
def test_get_mission_by_invalid_id(mission_reader, mission_id):
    with pytest.raises(Exception):
        mission_reader.get_mission_by_id(mission_id)


def test_valid_predefined_missions_files(mission_reader):
    # Checks that the predefined mission folder contains only valid missions!
    mission_list_dict = mission_reader.get_predefined_missions()
    predefined_mission_folder = Path(
        config.get("DEFAULT", "predefined_missions_folder")
    )
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
    assert task.name == "take_thermal_image"
    assert hasattr(task, "id")
    assert hasattr(task, "tag_id")


def test_mission_dependencies(mission_reader):
    mission_path = Path("./tests/test_data/test_mission_working.json")
    mission: Mission = mission_reader.read_mission_from_file(mission_path)
    mission.set_task_dependencies()

    task_dependencies = [None, None, [1], None, [0], [1, 2]]

    for index, tasks in enumerate(mission.tasks):
        assert tasks.depends_on == task_dependencies[index]
