from pathlib import Path

import pytest

from isar.config import config
from isar.models.mission import Mission
from tests.utilities import Utilities


@pytest.mark.parametrize(
    "mission_path ,expected_output",
    [
        (
            Path("./tests/test_data/test_mission_working_nosteps.json"),
            Mission,
        ),
        (Path("./tests/test_data/test_mission_working.json"), Mission),
    ],
)
def test_get_mission(mission_reader, mission_path, expected_output):
    output = mission_reader.read_mission_from_file(mission_path)
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
def test_get_misison_by_invalid_id(mission_reader, mission_id):
    with pytest.raises(Exception):
        mission_reader.get_mission_by_id(mission_id)


@pytest.mark.parametrize(
    "mission_id ,expected_output",
    [(1, True), (12345, False), (None, False)],
)
def test_is_mission_id_valid(mission_reader, mission_id, expected_output):
    output = mission_reader.mission_id_valid(mission_id)
    assert output == expected_output


@pytest.mark.parametrize(
    "mission_id",
    [config],
)
def test_mission_id_is_invalid(mission_reader, mission_id):
    with pytest.raises(Exception):
        mission_reader.mission_id_valid(mission_id)


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
        mission = mission_reader.read_mission_from_file(path_to_file)
        assert mission is not None
