import pytest

from isar.state_machine.states.monitor import Monitor
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import StepStatus
from robot_interface.models.mission.step import Step, TakeImage
from robot_interface.models.mission.task import Task
from tests.mocks.step import MockStep


@pytest.mark.parametrize(
    "mock_status, expected_output",
    [
        (StepStatus.Successful, True),
        (StepStatus.Successful, True),
        (StepStatus.Failed, True),
    ],
)
def test_step_finished(monitor: Monitor, mock_status, expected_output):
    step: Step = MockStep.drive_to
    step.status = mock_status
    step_completed: bool = monitor._step_finished(
        step=step,
    )

    assert step_completed == expected_output


@pytest.mark.parametrize(
    "mock_status, should_queue_upload",
    [
        (StepStatus.Successful, True),
        (StepStatus.Failed, False),
    ],
)
def test_should_only_upload_if_status_is_completed(
    monitor: Monitor, mock_status, should_queue_upload
):
    step: TakeImage = MockStep.take_image_in_coordinate_direction
    step.status = mock_status
    task: Task = Task(steps=[step])
    mission: Mission = Mission(tasks=[task])

    monitor.state_machine.current_mission = mission
    monitor.state_machine.current_task = task
    monitor.state_machine.current_step = step

    if monitor._should_upload_inspections():
        monitor._queue_inspections_for_upload(step)

    assert monitor.state_machine.queues.upload_queue.empty() == (
        not should_queue_upload
    )
