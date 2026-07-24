from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State
from isar.state_machine.states.await_next_mission import AwaitNextMission
from isar.state_machine.states.intervention_needed import InterventionNeeded
from isar.state_machine.states.stopping_unknown_mission import StoppingUnknownMission
from isar.state_machine.states.unknown_status import UnknownStatus
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.status import RobotStatus


def test_unknown_mission_successfully_stopped(events: Events) -> None:
    current_state = StoppingUnknownMission(events)

    stopping_state_event_handler: EventHandlerMapping | None = (
        current_state.get_event_handler_by_name("successful_stop_event")
    )
    assert stopping_state_event_handler is not None

    transition = stopping_state_event_handler.handler(EmptyMessage())

    assert events.mqtt_queue.qsize() == 0

    current_state = transition(events)

    assert type(current_state) is AwaitNextMission


def test_unknown_mission_successfully_stopped_with_no_mission_found(
    events: Events,
) -> None:
    current_state = StoppingUnknownMission(events)

    stopping_state_event_handler: EventHandlerMapping | None = (
        current_state.get_event_handler_by_name("mission_already_done_event")
    )
    assert stopping_state_event_handler is not None

    transition = stopping_state_event_handler.handler(EmptyMessage())

    assert events.mqtt_queue.qsize() == 0

    current_state = transition(events)

    assert type(current_state) is AwaitNextMission


def test_unknown_mission_successfully_aborted_on_isar_restart(events: Events) -> None:
    current_state: State = UnknownStatus(events)

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "robot_status_event"
    )
    assert event_handler is not None

    transition = event_handler.handler(RobotStatus.Busy)

    assert transition is not None

    current_state = transition(events)

    assert current_state is not None
    assert type(current_state) is StoppingUnknownMission

    stopping_state_event_handler: EventHandlerMapping | None = (
        current_state.get_event_handler_by_name("successful_stop_event")
    )
    assert stopping_state_event_handler is not None

    transition = stopping_state_event_handler.handler(EmptyMessage())

    current_state = transition(events)

    assert type(current_state) is AwaitNextMission


def test_stopping_mission_fails(events: Events) -> None:
    current_state = StoppingUnknownMission(events)
    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "failed_stop_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(
        ErrorMessage(error_description="", error_reason=ErrorReason.RobotAPIException)
    )

    assert events.mqtt_queue.empty()

    current_state = transition(events)
    assert type(current_state) is InterventionNeeded
