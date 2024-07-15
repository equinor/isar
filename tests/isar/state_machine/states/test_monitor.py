import pytest

from isar.state_machine.states.monitor import Monitor
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus, StepStatus
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
    step: Step = MockStep.drive_to()
    step.status = mock_status
    step_completed: bool = monitor._is_step_finished(
        step=step,
    )

    assert step_completed == expected_output


@pytest.mark.parametrize(
    "is_status_successful, should_queue_upload",
    [
        (True, True),
        (False, False),
    ],
)
def test_should_only_upload_if_status_is_completed(
    monitor: Monitor, is_status_successful, should_queue_upload
):
    step: TakeImage = MockStep.take_image_in_coordinate_direction()
    step.status = StepStatus.Successful if is_status_successful else StepStatus.Failed
    task: Task = Task(steps=[step])
    mission: Mission = Mission(tasks=[task])
    mission.status = (
        MissionStatus.Successful if is_status_successful else MissionStatus.Failed
    )

    monitor.state_machine.current_mission = mission
    monitor.state_machine.current_task = task
    monitor.state_machine.current_step = step

    if monitor._should_upload_inspections():
        monitor._queue_inspections_for_upload(mission, step)

    assert monitor.state_machine.queues.upload_queue.empty() == (
        not should_queue_upload
    )
