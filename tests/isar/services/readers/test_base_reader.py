from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest

from isar.models.mission import Mission
from isar.services.readers.base_reader import BaseReader
from robot_interface.models.geometry.pose import Pose
from robot_interface.models.mission import Task
from tests.mocks.mission_definition import mock_mission_definition
from tests.mocks.robot_variables import mock_pose
from tests.mocks.task import MockTask
from tests.utilities import Utilities


class TestBaseReader:
    @pytest.mark.parametrize(
        "location, expected_output",
        [
            (Path("./tests/test_data/test_mission_nofile.json"), None),
            (Path("./tests/test_data/test_mission_working_notasks.json"), dict),
            (Path("./tests/test_data/test_mission_working.json"), dict),
            (Path("./tests/test_data/test_mission_not_working.json"), dict),
            (Path("./tests/test_data/test_json_file.json"), list),
        ],
    )
    def test_read_json(self, location, expected_output):
        try:
            content = BaseReader.read_json(location)
        except Exception:
            content = None
        assert Utilities.compare_two_arguments(content, expected_output)

    @pytest.mark.parametrize(
        "dataclass_dict, expected_dataclass",
        [
            (asdict(mock_mission_definition("long_mission")), Mission),
            (asdict(MockTask.drive_to()), Task),
            (asdict(MockTask.take_image_in_coordinate_direction()), Task),
            (asdict(mock_pose()), Pose),
        ],
    )
    def test_dict_to_dataclass(self, dataclass_dict: dict, expected_dataclass: Any):
        content = BaseReader.dict_to_dataclass(dataclass_dict, expected_dataclass)
        assert type(content) is expected_dataclass
