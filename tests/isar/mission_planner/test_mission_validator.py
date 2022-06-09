import pytest

from isar.mission_planner.mission_validator import is_robot_capable_of_mission
from tests.mocks.mission_definition import MockMissionDefinition


@pytest.mark.parametrize(
    "mission,capabilities,expected_return",
    [
        (MockMissionDefinition.default_mission, ["drive_to_pose"], False),
        (MockMissionDefinition.default_mission, ["drive_to_pose", "take_image"], True),
    ],
)
def test_is_robot_capable_of_mission(mission, capabilities, expected_return) -> None:
    return_value, missing_capabilities = is_robot_capable_of_mission(
        mission=mission, robot_capabilities=capabilities
    )
    assert return_value == expected_return
