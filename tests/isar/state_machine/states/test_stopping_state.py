from typing import Optional, cast

from isar.eventhandlers.eventhandler import EventHandlerMapping, State
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.await_next_mission import AwaitNextMission
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states.returning_home import ReturningHome
from isar.state_machine.states.stopping import Stopping
from isar.state_machine.states.unknown_status import UnknownStatus
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.status import RobotStatus


def test_mqtt_message_not_sent_on_mission_stopped(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(90.0)
    sync_state_machine.current_state = Stopping(sync_state_machine, "mission_id")

    stopping_state: State = cast(State, sync_state_machine.current_state)
    stopping_state_event_handler: Optional[EventHandlerMapping] = (
        stopping_state.get_event_handler_by_name("successful_stop_event")
    )
    assert stopping_state_event_handler is not None

    transition = stopping_state_event_handler.handler(True)

    assert sync_state_machine.events.mqtt_queue.empty() is True

    sync_state_machine.current_state = transition(sync_state_machine)

    assert type(sync_state_machine.current_state) is AwaitNextMission


def test_unknown_mission_successfully_aborted_on_isar_restart(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = UnknownStatus(sync_state_machine)

    unknown_status_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        unknown_status_state.get_event_handler_by_name("robot_status_event")
    )
    assert event_handler is not None

    sync_state_machine.shared_state.robot_status.trigger_event(RobotStatus.Busy)

    transition = event_handler.handler(True)

    assert transition is not None

    sync_state_machine.current_state = transition(sync_state_machine)

    assert type(sync_state_machine.current_state) is Stopping

    stopping_state: State = cast(State, sync_state_machine.current_state)
    stopping_state_event_handler: Optional[EventHandlerMapping] = (
        stopping_state.get_event_handler_by_name("successful_stop_event")
    )
    assert stopping_state_event_handler is not None

    sync_state_machine.shared_state.robot_battery_level.trigger_event(90.0)

    transition = stopping_state_event_handler.handler(True)

    sync_state_machine.current_state = transition(sync_state_machine)

    assert type(sync_state_machine.current_state) is AwaitNextMission


def test_stopping_mission_fails(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Stopping(sync_state_machine, "mission_id")
    stopping_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
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
    sync_state_machine.shared_state.robot_battery_level.trigger_event(90.0)
    sync_state_machine.current_state = Stopping(sync_state_machine, "mission_id")
    stopping_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        stopping_state.get_event_handler_by_name("successful_stop_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(True)

    assert sync_state_machine.events.mqtt_queue.empty()

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is AwaitNextMission


def test_stopping_mission_succeeds_with_low_battery(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.current_state = Stopping(sync_state_machine, "mission_id")
    stopping_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        stopping_state.get_event_handler_by_name("successful_stop_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(True)

    assert sync_state_machine.events.mqtt_queue.empty()

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is ReturningHome
