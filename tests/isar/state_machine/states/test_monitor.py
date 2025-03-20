import pytest

from isar.state_machine.states.monitor import Monitor
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus, TaskStatus
from robot_interface.models.mission.task import TakeImage
from tests.mocks.task import MockTask


@pytest.mark.parametrize(
    "mock_status, expected_output",
    [
        (TaskStatus.Successful, True),
        (TaskStatus.Successful, True),
        (TaskStatus.Failed, True),
    ],
)
def test_task_finished(monitor: Monitor, mock_status, expected_output):
    task: TakeImage = MockTask.take_image()
    task.status = mock_status
    task_completed: bool = task.is_finished()
    assert task_completed == expected_output


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
    task: TakeImage = MockTask.take_image()
    task.status = TaskStatus.Successful if is_status_successful else TaskStatus.Failed
    mission: Mission = Mission(name="Dummy misson", tasks=[task])
    mission.status = (
        MissionStatus.Successful if is_status_successful else MissionStatus.Failed
    )

    monitor.state_machine.current_mission = mission
    monitor.state_machine.current_task = task

    if monitor._should_upload_inspections():
        monitor._queue_inspections_for_upload(mission, task)

    assert monitor.state_machine.events.upload_queue.empty() == (
        not should_queue_upload
    )
