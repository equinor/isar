from typing import cast

from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State
from isar.state_machine.states.await_next_mission import AwaitNextMission
from isar.state_machine.states.paused import Paused
from isar.state_machine.states.stopping_paused_mission import StoppingPausedMission
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason


def test_stopping_paused_mission_fails(events: Events) -> None:
    current_state = StoppingPausedMission(events, "mission_id")
    stopping_paused_mission_state: State = cast(State, current_state)
    event_handler: EventHandlerMapping | None = (
        stopping_paused_mission_state.get_event_handler_by_name("failed_stop_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(
        ErrorMessage(error_description="", error_reason=ErrorReason.RobotAPIException)
    )

    assert events.mqtt_queue.empty()

    current_state = transition(events)
    assert type(current_state) is Paused


def test_stopping_paused_mission_succeeds(events: Events) -> None:
    current_state = StoppingPausedMission(events, "mission_id")
    stopping_paused_mission_state: State = cast(State, current_state)
    event_handler: EventHandlerMapping | None = (
        stopping_paused_mission_state.get_event_handler_by_name("successful_stop_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    assert events.mqtt_queue.qsize() == 1

    current_state = transition(events)
    assert type(current_state) is AwaitNextMission
