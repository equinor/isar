import pytest
from isar.state_machine.states import Monitor
from models.enums.mission_status import MissionStatus
from models.enums.states import States

from tests.test_utilities.mock_interface.mock_robot_interface import MockRobot
from tests.test_utilities.mock_models.mock_step import MockStep


@pytest.mark.parametrize(
    "mission_in_progress, mock_mission_status, mock_mission_finished, expected_state",
    [
        (False, MissionStatus.Completed, True, States.Cancel),
        (True, MissionStatus.Completed, True, States.Send),
        (True, MissionStatus.InProgress, False, States.Monitor),
    ],
)
def test_monitor_mission(
    monitor,
    mocker,
    mission_in_progress,
    mock_mission_status,
    mock_mission_finished,
    expected_state,
):
    mocker.patch.object(
        MockRobot,
        "mission_status",
        return_value=mock_mission_status,
    )
    mocker.patch.object(
        Monitor,
        "mission_finished",
        return_value=mock_mission_finished,
    )
    mocker.patch.object(
        Monitor,
        "log_status",
        return_value=None,
    )

    monitor.state_machine.status.mission_in_progress = mission_in_progress
    monitor.state_machine.status.current_mission_step = MockStep.drive_to()
    next_state = monitor.monitor_mission()

    assert next_state is expected_state


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
    is_mission_finished: bool = monitor.mission_finished(
        mission_status=mock_status, instance_id=mission_instance_id
    )

    assert is_mission_finished == expected_output
