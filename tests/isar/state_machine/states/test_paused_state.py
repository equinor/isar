from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping
from isar.state_machine.states.paused import Paused
from isar.state_machine.states.pausing import Pausing
from isar.state_machine.states.stopping_go_to_recharge import StoppingGoToRecharge
from isar.state_machine.states.stopping_paused_mission import StoppingPausedMission


def test_transition_from_pausing_to_paused(events: Events) -> None:
    current_state = Pausing(events, "mission_id")

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "successful_pause_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is Paused


def test_transition_from_paused_to_stopping_paused_mission(events: Events) -> None:
    current_state = Paused(events, "test_id")

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "stop_mission_event"
    )

    assert event_handler is not None

    transition = event_handler.handler("test_id")

    current_state = transition(events)

    assert type(current_state) is StoppingPausedMission
    assert events.api_requests.stop_mission.response.has_event()


def test_transition_from_paused_to_stopping_to_recharge(events: Events) -> None:
    current_state = Paused(events, "test_id")

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "robot_battery_below_threshold_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)

    assert type(current_state) is StoppingGoToRecharge
    assert not events.api_requests.stop_mission.response.has_event()
    assert events.state_machine_events.stop_mission.has_event()


def test_stop_request_with_wrong_id_in_paused(events: Events) -> None:
    current_state = Paused(events, "test_id")

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "stop_mission_event"
    )

    assert event_handler is not None

    transition = event_handler.handler("wrong_test_id")

    assert transition is None
    assert events.api_requests.stop_mission.response.has_event()
