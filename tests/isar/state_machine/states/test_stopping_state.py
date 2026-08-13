from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping
from isar.state_machine.states.stopping import Stopping
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason


def test_mqtt_mission_status_sent_on_mission_stopped(events: Events) -> None:
    current_state = Stopping(events, "mission_id")

    stopping_state_event_handler: EventHandlerMapping = (
        current_state.get_event_handler_by_event(
            events.robot_service_events.mission_successfully_stopped
        )
    )

    transition = stopping_state_event_handler.handler(EmptyMessage())

    assert events.mqtt_queue.qsize() == 1

    current_state = transition(events)

    assert current_state.name is States.AwaitNextMission


def test_stopping_mission_fails(events: Events) -> None:
    current_state = Stopping(events, "mission_id")
    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.robot_service_events.mission_failed_to_stop
    )

    transition = event_handler.handler(
        ErrorMessage(error_description="", error_reason=ErrorReason.RobotAPIException)
    )

    assert events.mqtt_queue.empty()

    current_state = transition(events)
    assert current_state.name is States.Monitor
