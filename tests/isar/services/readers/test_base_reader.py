from dataclasses import asdict
from typing import Any

import pytest
from alitra import Pose

from isar.services.readers.base_reader import BaseReader
from robot_interface.models.mission.task import ReturnToHome, TakeImage
from tests.mocks.pose import MockPose
from tests.mocks.task import MockTask


class TestBaseReader:
    @pytest.mark.parametrize(
        "dataclass_dict, expected_dataclass",
        [
            (asdict(MockTask.return_home()), ReturnToHome),
            (asdict(MockPose.default_pose()), Pose),
        ],
    )
    def test_dict_to_dataclass(self, dataclass_dict: dict, expected_dataclass: Any):
        content = BaseReader.dict_to_dataclass(dataclass_dict, expected_dataclass)
        assert type(content) is expected_dataclass
