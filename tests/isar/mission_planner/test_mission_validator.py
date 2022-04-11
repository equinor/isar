import pytest

from isar.mission_planner.mission_validator import is_robot_capable_of_mission
from tests.mocks.mission_definition import mock_mission_definition


@pytest.mark.parametrize(
    "mission,capabilities,expected_return",
    [
        (mock_mission_definition(), ["drive_to_pose"], False),
        (mock_mission_definition(), ["drive_to_pose", "take_image"], True),
    ],
)
def test_is_robot_capable_of_mission(mission, capabilities, expected_return) -> None:
    return_value: bool = is_robot_capable_of_mission(
        mission=mission, robot_capabilities=capabilities
    )
    assert return_value == expected_return
