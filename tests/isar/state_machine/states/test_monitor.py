import logging

import pytest

from isar.eventhandlers.eventhandler import EventHandlerBase
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus, TaskStatus
from robot_interface.models.mission.task import TakeImage
from tests.test_double.task import StubTask

mock_logger = logging.getLogger("test_monitor_logger")


@pytest.mark.parametrize(
    "mock_status, expected_output",
    [
        (TaskStatus.Successful, True),
        (TaskStatus.Successful, True),
        (TaskStatus.Failed, True),
    ],
)
def test_task_finished(monitor: EventHandlerBase, mock_status, expected_output):
    task: TakeImage = StubTask.take_image()
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
    monitor: EventHandlerBase, is_status_successful, should_queue_upload
):
    task: TakeImage = StubTask.take_image()
    task.status = TaskStatus.Successful if is_status_successful else TaskStatus.Failed
    mission: Mission = Mission(name="Dummy misson", tasks=[task])
    mission.status = (
        MissionStatus.Successful if is_status_successful else MissionStatus.Failed
    )

    monitor.state_machine.current_mission = mission
    monitor.state_machine.current_task = task

    if monitor.state_machine.should_upload_inspections():
        monitor.state_machine.queue_inspections_for_upload(mission, task, mock_logger)

    assert monitor.state_machine.events.upload_queue.empty() == (
        not should_queue_upload
    )
