import asyncio
import json
from unittest.mock import call

import pytest
from pytest_mock import MockerFixture

from isar.config.settings import settings
from isar.models.events import EmptyMessage, Event, Events
from isar.robot.robot_service import RobotService
from isar.state_machine.state import State
from isar.state_machine.states.monitor import Monitor, transition_and_start_mission
from isar.state_machine.states.stopping import Stopping
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    ErrorReason,
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


@pytest.fixture
def service(events: Events, mocker: MockerFixture) -> RobotService:
    mocker.patch.object(settings, "FSM_SLEEP_TIME", 0)
    return RobotService(events, StubRobot(), events.mqtt_queue)


def test_stored_mission_is_forwarded_to_robot(
    stored_mission: Mission,
    service: RobotService,
    events: Events,
    mocker: MockerFixture,
) -> None:
    start = mocker.spy(service.robot, "initiate_mission")

    transition = transition_and_start_mission(events, stored_mission)
    transition.side_effect(events)

    success = service._start_mission_handler(
        events.action_requests.execute_mission.request.consume_event()
    )

    assert transition.state_def.name == States.Monitor
    assert success
    start.assert_called_once_with(stored_mission)


def test_adapter_rejection_uses_normal_failure_channel(
    stored_mission: Mission, service: RobotService, mocker: MockerFixture
) -> None:
    mocker.patch.object(
        service.robot,
        "initiate_mission",
        side_effect=RobotInfeasibleMissionException("Unknown stored routine"),
    )
    response = service.action_requests.execute_mission

    success = service._start_mission_handler(stored_mission)

    assert not success
    assert response.failure.consume_event() == ErrorMessage(
        ErrorReason.RobotInfeasibleMissionException,
        "Failed to initiate due to: Unknown stored routine",
    )
    assert not response.success.has_event()


@pytest.mark.parametrize(
    "terminal_status",
    [
        MissionStatus.Successful,
        MissionStatus.Failed,
        MissionStatus.Cancelled,
        MissionStatus.PartiallySuccessful,
    ],
)
def test_stored_monitor_reports_terminal_outcome(
    stored_mission: Mission,
    service: RobotService,
    terminal_status: MissionStatus,
    mocker: MockerFixture,
) -> None:
    recorder = service.mission_recorder = mocker.Mock()
    mocker.patch.object(
        service.robot,
        "mission_status",
        side_effect=[
            MissionStatus.NotStarted,
            MissionStatus.InProgress,
            MissionStatus.Paused,
            MissionStatus.InProgress,
            terminal_status,
        ],
    )
    response = service.action_requests.execute_mission

    asyncio.run(service._monitor_mission_handler(stored_mission))

    if terminal_status == MissionStatus.Successful:
        assert isinstance(response.success.consume_event(), EmptyMessage)
        assert not response.failure.has_event()
    else:
        assert response.failure.consume_event() == ErrorMessage(
            None, f"Stored mission reported as {terminal_status.value} by the robot"
        )
        assert not response.success.has_event()
    recorder.stop.assert_called_once_with(
        stored_mission.id, terminal_status != MissionStatus.Successful
    )


def test_stored_monitor_polls_mission_without_inspection_work(
    stored_mission: Mission,
    service: RobotService,
    events: Events,
    mocker: MockerFixture,
) -> None:
    mission_poll = mocker.patch.object(
        service.robot,
        "mission_status",
        side_effect=[MissionStatus.InProgress, MissionStatus.Successful],
    )
    task_poll = mocker.spy(service.robot, "task_status")

    asyncio.run(service._monitor_mission_handler(stored_mission))

    assert mission_poll.call_args_list == [call(stored_mission.id)] * 2
    task_poll.assert_not_called()
    assert not events.upload_task_event.has_event()
    assert events.mqtt_queue.empty()


def test_status_errors_cannot_report_success(
    stored_mission: Mission,
    service: RobotService,
    events: Events,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        service.robot,
        "mission_status",
        side_effect=RobotMissionStatusException("Unknown outcome"),
    )

    asyncio.run(service._monitor_mission_handler(stored_mission))

    assert events.action_requests.execute_mission.failure.has_event()
    assert not events.action_requests.execute_mission.success.has_event()
    assert stored_mission.status == MissionStatus.Failed


def test_stored_mission_stop_does_not_report_completion(
    stored_mission: Mission,
    service: RobotService,
    events: Events,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        service.robot, "mission_status", return_value=MissionStatus.InProgress
    )

    async def stop_mission() -> None:
        task = asyncio.create_task(service._monitor_mission_handler(stored_mission))
        await asyncio.sleep(0)
        await service._stop_mission_handler(task)

    asyncio.run(stop_mission())

    assert isinstance(
        events.action_requests.stop_mission.success.consume_event(), EmptyMessage
    )
    assert (
        events.action_requests.execute_mission.success.consume_event(),
        events.action_requests.execute_mission.failure.consume_event(),
    ) == (None, None)
    assert events.mqtt_queue.empty()


@pytest.mark.parametrize(
    "outcome",
    [MissionStatus.Successful, MissionStatus.Failed, MissionStatus.Cancelled],
)
def test_terminal_state_publishes_mission_outcome(
    stored_mission: Mission, events: Events, outcome: MissionStatus
) -> None:
    result_event: (
        Event[Mission | EmptyMessage] | Event[EmptyMessage] | Event[ErrorMessage]
    )
    result: EmptyMessage | ErrorMessage
    if outcome == MissionStatus.Cancelled:
        state = State(Stopping(events, stored_mission.id))
        result_event = events.action_requests.stop_mission.success
        result = EmptyMessage()
    else:
        state = State(Monitor(events, stored_mission.id))
        result_event = (
            events.action_requests.execute_mission.success
            if outcome == MissionStatus.Successful
            else events.action_requests.execute_mission.failure
        )
        result = (
            EmptyMessage()
            if outcome == MissionStatus.Successful
            else ErrorMessage(None, "Stored mission failed")
        )
    handler = state.get_event_handler_by_event(result_event)

    transition = handler.handler(result)

    next_state = State(transition.state_def)

    assert next_state.name == States.AwaitNextMission
    payload = json.loads(events.mqtt_queue.get().payload)
    assert {"mission_id": payload["mission_id"], "status": payload["status"]} == {
        "mission_id": stored_mission.id,
        "status": outcome.value,
    }
    assert {"task_id", "reason"}.isdisjoint(payload)
    assert events.mqtt_queue.empty()
