import pytest

from isar.state_machine.states import Monitor
from isar.state_machine.states_enum import States
from robot_interface.models.mission import MissionStatus
from tests.test_utilities.mock_interface.mock_robot_interface import MockRobot
from tests.test_utilities.mock_models.mock_step import MockStep


@pytest.mark.parametrize(
    "mission_instance_id, mock_status, expected_output",
    [
        (1, MissionStatus.Completed, True),
        (1, MissionStatus.Completed, True),
        (1, MissionStatus.Unexpected, False),
        (1, MissionStatus.Failed, True),
    ],
)
def test_mission_finished(
    monitor, mocker, mission_instance_id, mock_status, expected_output
):
    mission_finished: bool = monitor._mission_finished(
        mission_status=mock_status, instance_id=mission_instance_id
    )

    assert mission_finished == expected_output
