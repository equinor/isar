from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest

from isar.models.mission import Mission
from isar.services.readers.base_reader import BaseReader
from robot_interface.models.geometry.pose import Pose
from robot_interface.models.mission import Task
from tests.mocks.mission_definition import MockMissionDefinition
from tests.mocks.pose import MockPose
from tests.mocks.task import MockTask


class TestBaseReader:
    @pytest.mark.parametrize(
        "dataclass_dict, expected_dataclass",
        [
            (asdict(MockMissionDefinition.default_mission), Mission),
            (asdict(MockTask.drive_to), Task),
            (asdict(MockTask.take_image_in_coordinate_direction), Task),
            (asdict(MockPose.default_pose), Pose),
        ],
    )
    def test_dict_to_dataclass(self, dataclass_dict: dict, expected_dataclass: Any):
        content = BaseReader.dict_to_dataclass(dataclass_dict, expected_dataclass)
        assert type(content) is expected_dataclass
