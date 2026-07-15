from typing import cast

from isar.models.events import EmptyMessage
from isar.state_machine.state import EventHandlerMapping, State
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.await_next_mission import AwaitNextMission
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states.stopping import Stopping
from isar.state_machine.states.unknown_status import UnknownStatus
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.status import RobotStatus


def test_mqtt_mission_status_sent_on_mission_stopped(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Stopping(sync_state_machine, "mission_id")

    stopping_state: State = cast(State, sync_state_machine.current_state)
    stopping_state_event_handler: EventHandlerMapping | None = (
        stopping_state.get_event_handler_by_name("successful_stop_event")
    )
    assert stopping_state_event_handler is not None

    transition = stopping_state_event_handler.handler(EmptyMessage())

    assert sync_state_machine.events.mqtt_queue.qsize() == 1

    sync_state_machine.current_state = transition(sync_state_machine)

    assert type(sync_state_machine.current_state) is AwaitNextMission


def test_unknown_mission_successfully_aborted_on_isar_restart(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = UnknownStatus(sync_state_machine)

    unknown_status_state: State = cast(State, sync_state_machine.current_state)
    event_handler: EventHandlerMapping | None = (
        unknown_status_state.get_event_handler_by_name("robot_status_event")
    )
    assert event_handler is not None

    transition = event_handler.handler(RobotStatus.Busy)

    assert transition is not None

    sync_state_machine.current_state = transition(sync_state_machine)

    assert type(sync_state_machine.current_state) is Stopping

    stopping_state: State = cast(State, sync_state_machine.current_state)
    stopping_state_event_handler: EventHandlerMapping | None = (
        stopping_state.get_event_handler_by_name("successful_stop_event")
    )
    assert stopping_state_event_handler is not None

    transition = stopping_state_event_handler.handler(EmptyMessage())

    sync_state_machine.current_state = transition(sync_state_machine)

    assert type(sync_state_machine.current_state) is AwaitNextMission


def test_stopping_mission_fails(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Stopping(sync_state_machine, "mission_id")
    stopping_state: State = cast(State, sync_state_machine.current_state)
    event_handler: EventHandlerMapping | None = (
        stopping_state.get_event_handler_by_name("failed_stop_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(
        ErrorMessage(error_description="", error_reason=ErrorReason.RobotAPIException)
    )

    assert sync_state_machine.events.mqtt_queue.empty()

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is Monitor


def test_stopping_mission_succeeds(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Stopping(sync_state_machine, "mission_id")
    stopping_state: State = cast(State, sync_state_machine.current_state)
    event_handler: EventHandlerMapping | None = (
        stopping_state.get_event_handler_by_name("successful_stop_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    assert sync_state_machine.events.mqtt_queue.qsize() == 1

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is AwaitNextMission
