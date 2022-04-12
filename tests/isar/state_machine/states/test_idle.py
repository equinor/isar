import pytest

from isar.models.mission import Mission
from isar.state_machine.state_machine import StateMachine, States
from robot_interface.models.mission import DriveToPose
from tests.mocks.pose import MockPose


@pytest.mark.parametrize(
    "mock_should_start_mission, next_expected_state",
    [
        (
            (
                True,
                Mission([DriveToPose(pose=MockPose.default_pose)]),
            ),
            States.InitiateTask,
        ),
        ((False, None), States.Idle),
    ],
)
def test_idle_iterate(
    idle_state,
    mocker,
    mock_should_start_mission,
    next_expected_state,
):
    mocker.patch.object(
        StateMachine, "should_start_mission", return_value=mock_should_start_mission
    )
    next_state: States = idle_state._get_next_state()
    assert next_state == next_expected_state
