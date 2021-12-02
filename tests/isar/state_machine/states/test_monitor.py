import pytest

from robot_interface.models.mission import TaskStatus


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
    task_completed: bool = monitor._task_completed(
        task_status=mock_status,
    )

    assert task_completed == expected_output
