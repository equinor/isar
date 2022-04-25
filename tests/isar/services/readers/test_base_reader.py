from dataclasses import asdict
from typing import Any

import pytest
from alitra import Pose

from isar.models.mission import Mission
from isar.services.readers.base_reader import BaseReader
from robot_interface.models.mission import Step
from tests.mocks.mission_definition import MockMissionDefinition
from tests.mocks.pose import MockPose
from tests.mocks.step import MockStep


class TestBaseReader:
    @pytest.mark.parametrize(
        "dataclass_dict, expected_dataclass",
        [
            (asdict(MockMissionDefinition.default_mission), Mission),
            (asdict(MockStep.drive_to), Step),
            (asdict(MockStep.take_image_in_coordinate_direction), Step),
            (asdict(MockPose.default_pose), Pose),
        ],
    )
    def test_dict_to_dataclass(self, dataclass_dict: dict, expected_dataclass: Any):
        content = BaseReader.dict_to_dataclass(dataclass_dict, expected_dataclass)
        assert type(content) is expected_dataclass
