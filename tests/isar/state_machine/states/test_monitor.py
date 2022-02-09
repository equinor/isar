import pytest

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
def test_task_completed(monitor, mock_status, expected_output):
    task: Task = MockTask.drive_to()
    task.status = mock_status
    task_completed: bool = monitor._task_completed(
        task=task,
    )

    assert task_completed == expected_output
