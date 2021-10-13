import pytest

from isar.state_machine.states import Send
from isar.state_machine.states_enum import States
from tests.test_utilities.mock_interface.mock_robot_interface import MockRobot
from tests.test_utilities.mock_models.mock_step import MockStep


@pytest.mark.parametrize(
    "current_mission_step, mission_in_progress, mock_return, expected_state",
    [
        (
            MockStep.drive_to(),
            False,
            {
                "schedule_step": (False, 1, None),
                "handle_send_failure": States.Cancel,
            },
            States.Cancel,
        ),
        (
            MockStep.take_image_in_coordinate_direction(),
            True,
            {
                "schedule_step": (True, 1, None),
                "handle_send_failure": States.Cancel,
            },
            States.Monitor,
        ),
    ],
)
def test_send_mission(
    send,
    mocker,
    current_mission_step,
    mission_in_progress,
    mock_return,
    expected_state,
):
    send.state_machine.status.mission_in_progress = mission_in_progress
    send.state_machine.status.current_mission_step = current_mission_step

    mocker.patch.object(
        MockRobot, "schedule_step", return_value=mock_return["schedule_step"]
    )
    mocker.patch.object(
        Send,
        "handle_send_failure",
        return_value=mock_return["handle_send_failure"],
    )
    next_state = send.send_mission(current_mission_step)

    assert next_state is expected_state


@pytest.mark.parametrize(
    "current_mission_step, send_failure_counter_limit, send_failure_counter, mock_return, expected_state",
    [
        (MockStep.drive_to(), 5, 1, {"mission_scheduled": False}, States.Send),
        (MockStep.drive_to(), 5, 5, {"mission_scheduled": False}, States.Cancel),
        (MockStep.drive_to(), 5, 2, {"mission_scheduled": True}, States.Monitor),
    ],
)
def test_handle_send_failure(
    send,
    mocker,
    current_mission_step,
    send_failure_counter_limit,
    send_failure_counter,
    mock_return,
    expected_state,
):
    send.send_failure_counter_limit = send_failure_counter_limit
    send.send_failure_counter = send_failure_counter
    mocker.patch.object(
        MockRobot,
        "mission_scheduled",
        return_value=mock_return["mission_scheduled"],
    )
    next_state = send.handle_send_failure(current_mission_step)
    assert next_state is expected_state
