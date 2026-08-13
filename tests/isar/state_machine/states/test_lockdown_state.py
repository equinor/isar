from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping
from isar.state_machine.states.going_to_lockdown import GoingToLockdown
from isar.state_machine.states.lockdown import Lockdown
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states.stopping_go_to_lockdown import StoppingGoToLockdown


def test_mission_stopped_when_going_to_lockdown(events: Events) -> None:
    current_state = Monitor(events, "mission_id")

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.api_requests.send_to_lockdown.request
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is StoppingGoToLockdown


def test_going_to_lockdown_transitions_to_lockdown(events: Events) -> None:
    current_state = GoingToLockdown(events)

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.robot_service_events.mission_succeeded
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is Lockdown
