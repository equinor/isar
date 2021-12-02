import pytest

from robot_interface.models.mission import MissionStatus


@pytest.mark.parametrize(
    "mock_status, expected_output",
    [
        (MissionStatus.Completed, True),
        (MissionStatus.Completed, True),
        (MissionStatus.Unexpected, False),
        (MissionStatus.Failed, True),
    ],
)
def test_mission_finished(monitor, mock_status, expected_output):
    mission_finished: bool = monitor._mission_finished(
        mission_status=mock_status,
    )

    assert mission_finished == expected_output
