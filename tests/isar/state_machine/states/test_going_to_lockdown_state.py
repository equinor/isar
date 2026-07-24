from isar.config.settings import settings
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State
from isar.state_machine.states.await_next_mission import AwaitNextMission
from isar.state_machine.states.going_to_lockdown import GoingToLockdown
from isar.state_machine.states.going_to_recharging import GoingToRecharging
from isar.state_machine.states.intervention_needed import InterventionNeeded
from isar.state_machine.states.return_home_paused import ReturnHomePaused
from isar.state_machine.states.returning_home import ReturningHome
from isar.state_machine.states.stopping_go_to_lockdown import StoppingGoToLockdown
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason


def test_transition_from_return_home_paused_to_going_to_lockdown(
    events: Events,
) -> None:
    current_state: State = ReturnHomePaused(events)

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "send_to_lockdown_event"
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)

    assert events.api_requests.send_to_lockdown.response.has_event()
    assert type(current_state) is GoingToLockdown

    lockdown_event_handler: EventHandlerMapping | None = (
        current_state.get_event_handler_by_name("mission_failed_to_resume")
    )
    assert lockdown_event_handler is not None

    transition = lockdown_event_handler.handler(
        ErrorMessage(
            error_description="Test going to lockdown resume return to home mission failed",
            error_reason=ErrorReason.RobotCommunicationException,
        )
    )

    current_state = transition(events)
    assert type(current_state) is InterventionNeeded


def test_stopping_lockdown_transitions_to_going_to_lockdown(events: Events) -> None:
    current_state = StoppingGoToLockdown(events, "mission_id")

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "successful_stop_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is GoingToLockdown

    assert events.api_requests.send_to_lockdown.response.check().lockdown_started

    assert not events.mqtt_queue.empty()
    mqtt_message = events.mqtt_queue.get(block=False)
    assert mqtt_message is not None
    mqtt_payload_topic = mqtt_message[0]
    assert mqtt_payload_topic is settings.TOPIC_ISAR_MISSION_ABORTED


def test_return_home_transitions_to_going_to_lockdown(events: Events) -> None:
    current_state = ReturningHome(events)

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "send_to_lockdown_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is GoingToLockdown


def test_recharging_transitions_to_going_to_lockdown(events: Events) -> None:
    current_state = GoingToRecharging(events)

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "send_to_lockdown_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is GoingToLockdown


def test_await_next_mission_transitions_to_going_to_lockdown(events: Events) -> None:
    current_state = AwaitNextMission(events)

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "send_to_lockdown_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is GoingToLockdown

    assert events.api_requests.send_to_lockdown.response.check()
