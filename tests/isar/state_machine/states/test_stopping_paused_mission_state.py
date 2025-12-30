from typing import Optional, cast

from isar.eventhandlers.eventhandler import EventHandlerMapping, State
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.await_next_mission import AwaitNextMission
from isar.state_machine.states.paused import Paused
from isar.state_machine.states.returning_home import ReturningHome
from isar.state_machine.states.stopping_paused_mission import StoppingPausedMission
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason


def test_stopping_paused_mission_fails(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = StoppingPausedMission(
        sync_state_machine, "mission_id"
    )
    stopping_paused_mission_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        stopping_paused_mission_state.get_event_handler_by_name("failed_stop_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(
        ErrorMessage(error_description="", error_reason=ErrorReason.RobotAPIException)
    )

    assert sync_state_machine.events.mqtt_queue.empty()

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is Paused


def test_stopping_paused_mission_succeeds(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(90.0)
    sync_state_machine.current_state = StoppingPausedMission(
        sync_state_machine, "mission_id"
    )
    stopping_paused_mission_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        stopping_paused_mission_state.get_event_handler_by_name("successful_stop_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(True)

    assert sync_state_machine.events.mqtt_queue.empty()

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is AwaitNextMission


def test_stopping_paused_mission_succeeds_with_low_battery(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.current_state = StoppingPausedMission(
        sync_state_machine, "mission_id"
    )
    stopping_paused_mission_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        stopping_paused_mission_state.get_event_handler_by_name("successful_stop_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(True)

    assert sync_state_machine.events.mqtt_queue.empty()

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is ReturningHome
