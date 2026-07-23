from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping
from isar.state_machine.states.going_to_lockdown import GoingToLockdown
from isar.state_machine.states.lockdown import Lockdown
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states.stopping_go_to_lockdown import StoppingGoToLockdown


def test_mission_stopped_when_going_to_lockdown(events: Events) -> None:
    current_state = Monitor(events, "mission_id")

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "send_to_lockdown_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is StoppingGoToLockdown


def test_going_to_lockdown_transitions_to_lockdown(events: Events) -> None:
    current_state = GoingToLockdown(events)

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "mission_succeeded_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is Lockdown
