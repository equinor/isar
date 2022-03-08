import pytest

from isar.state_machine.states.monitor import Monitor
from robot_interface.models.mission import Task, TaskStatus
from tests.mocks.task import MockTask


@pytest.mark.parametrize(
    "mock_status, expected_output",
    [
        (TaskStatus.Completed, True),
        (TaskStatus.Completed, True),
        (TaskStatus.Unexpected, False),
        (TaskStatus.Failed, True),
    ],
)
def test_task_finished(monitor: Monitor, mock_status, expected_output):
    task: Task = MockTask.drive_to()
    task.status = mock_status
    task_completed: bool = monitor._task_finished(
        task=task,
    )

    assert task_completed == expected_output


@pytest.mark.parametrize(
    "mock_status, should_queue_upload",
    [
        (TaskStatus.Completed, True),
        (TaskStatus.Failed, False),
    ],
)
def test_should_only_upload_if_status_is_completed(
    monitor: Monitor, mock_status, should_queue_upload
):
    task: Task = MockTask.take_image_in_coordinate_direction()
    task.status = mock_status
    monitor._process_finished_task(task)
    assert monitor.state_machine.queues.upload_queue.empty() == (
        not should_queue_upload
    )
