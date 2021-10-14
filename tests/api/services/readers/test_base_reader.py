from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest

from isar.models.mission import Mission
from isar.services.readers.base_reader import BaseReader
from robot_interface.models.geometry.joints import Joints
from robot_interface.models.geometry.pose import Pose
from robot_interface.models.mission import Step
from tests.test_utilities.mock_models.mock_mission_definition import (
    mock_mission_definition,
)
from tests.test_utilities.mock_models.mock_robot_variables import mock_joints, mock_pose
from tests.test_utilities.mock_models.mock_step import MockStep
from tests.utilities import Utilities


class TestBaseReader:
    @pytest.mark.parametrize(
        "location, expected_output",
        [
            (Path("./tests/test_data/test_mission_nofile.json"), None),
            (Path("./tests/test_data/test_mission_working_nosteps.json"), dict),
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
            (asdict(MockStep.drive_to()), Step),
            (asdict(MockStep.take_image_in_coordinate_direction()), Step),
            (asdict(mock_pose()), Pose),
            (asdict(mock_joints()), Joints),
        ],
    )
    def test_dict_to_dataclass(self, dataclass_dict: dict, expected_dataclass: Any):
        content = BaseReader.dict_to_dataclass(dataclass_dict, expected_dataclass)
        assert type(content) is expected_dataclass
