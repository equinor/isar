import asyncio
import json

import pytest
from pytest_mock import MockerFixture

from isar.config.settings import settings
from isar.models.events import EmptyMessage, Events
from isar.robot.robot_service import RobotService
from isar.state_machine.state import State
from isar.state_machine.states.monitor import Monitor, transition_and_start_mission
from isar.state_machine.states.stopping import Stopping
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    RobotInfeasibleMissionException,
    RobotMissionStatusException,
)
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus
from tests.test_mocks.robot_interface import StubRobot


@pytest.fixture
def stored_mission() -> Mission:
    return Mission(
        id="run-id",
        name="Weekly diagnostic",
        robot_mission_id="DiagnosticRoutine",
    )


def test_adapter_rejection_uses_normal_failure_channel(
    stored_mission: Mission, mocker: MockerFixture
) -> None:
    events = Events()
    robot = StubRobot()
    mocker.patch.object(
        robot,
        "initiate_mission",
        side_effect=RobotInfeasibleMissionException("Unknown stored routine"),
    )
    service = RobotService(events, robot, events.mqtt_queue)
    recorder = service.mission_recorder = mocker.Mock()
    assert not service._start_mission_handler(stored_mission)
    assert events.action_requests.execute_mission.failure.has_event()
    assert not events.action_requests.execute_mission.success.has_event()
    recorder.start.assert_not_called()


@pytest.mark.parametrize(
    "terminal_status",
    [
        MissionStatus.Successful,
        MissionStatus.Failed,
        MissionStatus.Cancelled,
        MissionStatus.PartiallySuccessful,
    ],
)
def test_normal_monitor_uses_robot_mission_outcome_without_tasks(
    stored_mission: Mission, terminal_status: MissionStatus, mocker: MockerFixture
) -> None:
    events = Events()
    robot = StubRobot()
    service = RobotService(events, robot, events.mqtt_queue)
    recorder = service.mission_recorder = mocker.Mock()
    start = mocker.spy(robot, "initiate_mission")
    assert transition_and_start_mission(stored_mission)(events).name == States.Monitor
    assert service._start_mission_handler(
        events.action_requests.execute_mission.request.consume_event()
    )
    start.assert_called_once_with(stored_mission)
    recorder.start.assert_called_once_with(stored_mission.id)
    mocker.patch.object(settings, "FSM_SLEEP_TIME", 0)
    statuses = iter(
        [
            MissionStatus.NotStarted,
            MissionStatus.InProgress,
            MissionStatus.Paused,
            MissionStatus.InProgress,
            terminal_status,
        ]
    )

    def mission_status(mission_id: str) -> MissionStatus:
        assert mission_id == stored_mission.id
        return next(statuses)

    mocker.patch.object(robot, "mission_status", side_effect=mission_status)
    task_poll = mocker.spy(robot, "task_status")
    asyncio.run(service._monitor_mission_handler(stored_mission))
    recorder.stop.assert_called_once_with(
        stored_mission.id, terminal_status != MissionStatus.Successful
    )
    result_event = (
        events.action_requests.execute_mission.success
        if terminal_status == MissionStatus.Successful
        else events.action_requests.execute_mission.failure
    )
    result = result_event.consume_event()
    if terminal_status == MissionStatus.Successful:
        assert isinstance(result, EmptyMessage)
        assert not events.action_requests.execute_mission.failure.has_event()
    else:
        assert isinstance(result, ErrorMessage)
        assert terminal_status.value in result.error_description
        assert not events.action_requests.execute_mission.success.has_event()
    state = State(Monitor(events, stored_mission.id))
    handler = state.get_event_handler_by_event(result_event)
    assert State(handler.handler(result)(events)).name == States.AwaitNextMission
    payloads = []
    while not events.mqtt_queue.empty():
        payloads.append(json.loads(events.mqtt_queue.get().payload))
    assert all("task_id" not in payload for payload in payloads)
    assert payloads[-1]["mission_id"] == stored_mission.id
    assert payloads[-1]["status"] == (
        MissionStatus.Successful.value
        if terminal_status == MissionStatus.Successful
        else MissionStatus.Failed.value
    )
    task_poll.assert_not_called()
    assert not events.upload_task_event.has_event()


def test_status_errors_cannot_report_success(
    stored_mission: Mission, mocker: MockerFixture
) -> None:
    events = Events()
    robot = StubRobot(mission_status=MissionStatus.InProgress)
    service = RobotService(events, robot, events.mqtt_queue)
    mocker.patch.object(settings, "FSM_SLEEP_TIME", 0)
    mocker.patch.object(
        robot,
        "mission_status",
        side_effect=RobotMissionStatusException("Unknown outcome"),
    )
    asyncio.run(service._monitor_mission_handler(stored_mission))
    assert events.action_requests.execute_mission.failure.has_event()
    assert not events.action_requests.execute_mission.success.has_event()
    assert stored_mission.status == MissionStatus.Failed


def test_stored_mission_user_stop_reports_cancelled(stored_mission: Mission) -> None:
    events = Events()
    robot = StubRobot(mission_status=MissionStatus.InProgress)
    service = RobotService(events, robot, events.mqtt_queue)

    async def stop_mission() -> None:
        task = asyncio.create_task(service._monitor_mission_handler(stored_mission))
        await asyncio.sleep(0)
        await service._stop_mission_handler(task)

    asyncio.run(stop_mission())
    result_event = events.action_requests.stop_mission.success
    result = result_event.consume_event()
    assert isinstance(result, EmptyMessage)
    assert not events.action_requests.execute_mission.success.has_event()
    assert not events.action_requests.execute_mission.failure.has_event()
    assert stored_mission._get_unfinished_tasks() == []
    assert events.mqtt_queue.empty()
    state = State(Stopping(events, stored_mission.id))
    handler = state.get_event_handler_by_event(result_event)
    assert State(handler.handler(result)(events)).name == States.AwaitNextMission
    payload = json.loads(events.mqtt_queue.get().payload)
    assert events.mqtt_queue.empty()
    assert payload["mission_id"] == stored_mission.id
    assert payload["status"] == MissionStatus.Cancelled.value
    assert "reason" not in payload
