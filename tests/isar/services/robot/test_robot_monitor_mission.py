import asyncio
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from isar.config.settings import settings
from isar.models.mqtt_queue import MQTTQueue
from isar.robot.robot_monitor_mission import (
    robot_monitor_mission,
    robot_monitor_return_home_mission,
)
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus, TaskStatus
from robot_interface.models.mission.task import TakeImage
from tests.test_mocks.inspection import stub_pose
from tests.test_mocks.robot_interface import StubRobot


@pytest.fixture(autouse=True)
def zero_sleep(mocker: MockerFixture) -> None:
    mocker.patch.object(settings, "FSM_SLEEP_TIME", 0)
    mocker.patch.object(settings, "REQUEST_STATUS_COMMUNICATION_RECONNECT_DELAY", 0)


def _make_task(task_id: str) -> TakeImage:
    return TakeImage(
        id=task_id,
        robot_pose=stub_pose(),
        target=stub_pose().position,
    )


def test_mission_drains_remaining_tasks_after_success(mocker: MockerFixture) -> None:
    task1 = _make_task("task-1")
    task2 = _make_task("task-2")
    mission = Mission(id="m-1", name="Test", tasks=[task1, task2])
    robot = StubRobot()
    mocker.patch.object(
        robot,
        "mission_status",
        side_effect=[MissionStatus.InProgress, MissionStatus.Successful],
    )
    mocker.patch.object(
        robot,
        "task_status",
        side_effect=[
            TaskStatus.InProgress,
            TaskStatus.Successful,
            TaskStatus.Successful,
        ],
    )
    upload = Mock()
    mqtt_queue = Mock(spec=MQTTQueue)

    error_message, _, is_aborted = asyncio.run(
        robot_monitor_mission(mission, robot, upload, mqtt_queue)
    )

    assert error_message is None
    assert not is_aborted
    assert task1.status == TaskStatus.Successful
    assert task2.status == TaskStatus.Successful
    assert upload.call_count == 2


@pytest.mark.parametrize(
    ("mission_status", "expected_task_status"),
    [
        (MissionStatus.Failed, TaskStatus.Failed),
        (MissionStatus.Cancelled, TaskStatus.Cancelled),
    ],
)
def test_failed_or_cancelled_mission_publishes_terminal_task_status(
    mocker: MockerFixture,
    mission_status: MissionStatus,
    expected_task_status: TaskStatus,
) -> None:
    task = _make_task("task-1")
    mission = Mission(id="m-2", name="Test", tasks=[task])
    robot = StubRobot()
    mocker.patch.object(robot, "mission_status", return_value=mission_status)
    mqtt_queue = Mock(spec=MQTTQueue)

    error_message, _, is_aborted = asyncio.run(
        robot_monitor_mission(mission, robot, Mock(), mqtt_queue)
    )

    assert not is_aborted
    assert error_message == ErrorMessage(
        error_reason=None,
        error_description="The mission was reported as failed by the robot",
    )
    assert task.status == expected_task_status
    mqtt_queue.publish_task_status.assert_called_once_with(task, mission.id)


def test_return_home_mission_reports_failure(mocker: MockerFixture) -> None:
    robot = StubRobot()
    mocker.patch.object(
        robot,
        "mission_status",
        side_effect=[MissionStatus.InProgress, MissionStatus.Failed],
    )

    error_message, is_aborted = asyncio.run(
        robot_monitor_return_home_mission("rh-1", robot)
    )

    assert not is_aborted
    assert error_message == ErrorMessage(
        error_reason=None,
        error_description="The mission was reported as failed by the robot",
    )
