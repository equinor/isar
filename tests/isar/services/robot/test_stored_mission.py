import asyncio
import json
import logging
from threading import Event

import pytest
from pytest_mock import MockerFixture

from isar.config.settings import settings
from isar.models.events import EmptyMessage, Events
from isar.robot.robot_service import RobotService
from isar.robot.robot_start_mission import robot_start_mission
from isar.state_machine.state import State
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states.stopping_go_to_lockdown import StoppingGoToLockdown
from isar.state_machine.states.stopping_go_to_recharge import StoppingGoToRecharge
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorReason,
    RobotMissionStatusException,
)
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus
from tests.test_mocks.mission_definition import DummyMissionDefinition
from tests.test_mocks.robot_interface import StubRobot


@pytest.fixture
def stored_mission() -> Mission:
    return Mission(
        id="run-id", name="Weekly diagnostic", robot_mission_id="DiagnosticRoutine"
    )


def test_stored_mission_uses_explicit_hook(
    stored_mission: Mission, mocker: MockerFixture
) -> None:
    robot = StubRobot()
    start = mocker.patch.object(robot, "initiate_stored_mission")
    ordinary_start = mocker.spy(robot, "initiate_mission")
    error = robot_start_mission(
        Event(), robot, logging.getLogger("test"), stored_mission
    )
    assert error is None
    start.assert_called_once_with(stored_mission)
    ordinary_start.assert_not_called()


def test_unsupported_integration_cannot_execute_stored_mission(
    stored_mission: Mission, mocker: MockerFixture
) -> None:
    robot = StubRobot()
    ordinary_start = mocker.spy(robot, "initiate_mission")
    error = robot_start_mission(
        Event(), robot, logging.getLogger("test"), stored_mission
    )
    assert error is not None
    assert error.error_reason == ErrorReason.RobotInfeasibleMissionException
    ordinary_start.assert_not_called()


def test_task_mission_still_uses_existing_hook(mocker: MockerFixture) -> None:
    robot = StubRobot()
    stored_start = mocker.spy(robot, "initiate_stored_mission")
    ordinary_start = mocker.spy(robot, "initiate_mission")
    mission = DummyMissionDefinition.default_mission.model_copy(deep=True)
    error = robot_start_mission(Event(), robot, logging.getLogger("test"), mission)
    assert error is None
    ordinary_start.assert_called_once_with(mission)
    stored_start.assert_not_called()


@pytest.mark.parametrize(
    "terminal_status",
    [
        MissionStatus.Successful,
        MissionStatus.Failed,
        MissionStatus.Cancelled,
        MissionStatus.PartiallySuccessful,
    ],
)
def test_taskless_mission_lifecycle_reports_robot_outcome(
    stored_mission: Mission,
    terminal_status: MissionStatus,
    mocker: MockerFixture,
) -> None:
    events = Events()
    robot = StubRobot()
    service = RobotService(events, robot, events.mqtt_queue)
    mocker.patch.object(settings, "FSM_SLEEP_TIME", 0)
    mission_status = mocker.patch.object(
        robot,
        "mission_status",
        side_effect=[
            MissionStatus.NotStarted,
            MissionStatus.InProgress,
            MissionStatus.Paused,
            MissionStatus.InProgress,
            terminal_status,
        ],
    )
    task_status = mocker.spy(robot, "task_status")
    asyncio.run(service._monitor_mission_handler(stored_mission))

    state = State(Monitor(events, stored_mission.id))
    result_event = (
        events.action_requests.execute_mission.failure
        if terminal_status == MissionStatus.Failed
        else events.action_requests.execute_mission.success
    )
    handler = state.get_event_handler_by_event(result_event)
    transition = handler.handler(result_event.consume_event())
    assert State(transition(events)).name == States.AwaitNextMission
    payload = json.loads(events.mqtt_queue.get().payload)
    assert payload["mission_id"] == stored_mission.id
    assert payload["status"] == terminal_status
    assert mission_status.call_count == 5
    assert all(
        call.args == (stored_mission.id,) for call in mission_status.call_args_list
    )
    task_status.assert_not_called()
    assert not events.upload_task_event.has_event()


def test_taskless_status_failure_is_not_success(
    stored_mission: Mission, mocker: MockerFixture
) -> None:
    events = Events()
    robot = StubRobot()
    service = RobotService(events, robot, events.mqtt_queue)
    mocker.patch.object(
        robot,
        "mission_status",
        side_effect=RobotMissionStatusException("Cannot determine robot outcome"),
    )
    asyncio.run(service._monitor_mission_handler(stored_mission))
    assert events.action_requests.execute_mission.failure.has_event()
    assert not events.action_requests.execute_mission.success.has_event()


@pytest.mark.parametrize("lockdown", [False, True])
def test_interrupted_stored_mission_is_not_restarted(
    stored_mission: Mission, mocker: MockerFixture, lockdown: bool
) -> None:
    events = Events()
    robot = StubRobot(mission_status=MissionStatus.InProgress)
    service = RobotService(events, robot, events.mqtt_queue)
    task_status = mocker.spy(robot, "task_status")

    async def stop_while_monitoring() -> None:
        task = asyncio.create_task(service._monitor_mission_handler(stored_mission))
        await asyncio.sleep(0)
        await service._stop_mission_handler(task)

    asyncio.run(stop_while_monitoring())
    result_event = events.action_requests.stop_mission.success
    result = result_event.consume_event()
    assert isinstance(result, EmptyMessage)
    assert not events.action_requests.execute_mission.success.has_event()
    assert not events.action_requests.execute_mission.failure.has_event()
    aborted = json.loads(events.mqtt_queue.get().payload)
    assert aborted["mission_id"] == stored_mission.id
    assert "automatic restart is not supported" in aborted["reason"]
    state = State(
        StoppingGoToLockdown(events, stored_mission.id)
        if lockdown
        else StoppingGoToRecharge(events)
    )
    handler = state.get_event_handler_by_event(result_event)
    transition = handler.handler(result)
    assert State(transition(events)).name == (
        States.GoingToLockdown if lockdown else States.GoingToRecharging
    )
    task_status.assert_not_called()


def test_stored_mission_stopped_before_monitor_starts_is_aborted(
    stored_mission: Mission,
) -> None:
    events = Events()
    service = RobotService(events, StubRobot(), events.mqtt_queue)

    async def stop_before_monitoring() -> None:
        task = asyncio.create_task(service._monitor_mission_handler(stored_mission))
        await service._stop_mission_handler(task, stored_mission)

    asyncio.run(stop_before_monitoring())
    assert isinstance(
        events.action_requests.stop_mission.success.consume_event(), EmptyMessage
    )
    assert not events.action_requests.execute_mission.success.has_event()
    aborted = json.loads(events.mqtt_queue.get().payload)
    assert aborted["mission_id"] == stored_mission.id


def test_completed_stored_mission_is_not_aborted(stored_mission: Mission) -> None:
    events = Events()
    service = RobotService(events, StubRobot(), events.mqtt_queue)

    async def stop_after_completion() -> None:
        task = asyncio.create_task(service._monitor_mission_handler(stored_mission))
        await task
        await service._stop_mission_handler(task, stored_mission)

    asyncio.run(stop_after_completion())
    assert events.action_requests.execute_mission.success.has_event()
    assert events.mqtt_queue.empty()
