from collections.abc import Callable

from isar.models.events import Events
from isar.state_machine.state import State
from isar.state_machine.states_enum import States


def test_no_dupliate_state_names(all_states_dict: dict[States, State]) -> None:
    all_state_names = list(all_states_dict.keys())
    for state_name, state_object in all_states_dict.items():
        assert state_name == state_object.name
        assert (
            all_state_names.count(state_name) == 1
        ), f"{state_name.name} is used for more than one state"


def test_no_non_deterministic_eventhandlers(
    all_states_dict: dict[States, State],
) -> None:
    for state_name, state_object in all_states_dict.items():
        event_set = set()
        for handler in state_object.handlers:
            assert (
                not handler.event in event_set
            ), f"{state_name.name} has two handlers for event '{handler.event.name}'"
            event_set.add(handler.event)


def _get_events_hash(events: Events) -> str:
    api_requests = ",".join(
        [
            name + ":" + str(value.request.check()) + str(value.response.check())
            for name, value in events.api_requests.__dict__.items()
        ]
    )
    action_requests = ",".join(
        [
            name
            + ":"
            + str(value.failure.check())
            + str(value.request.check())
            + str(value.success.check())
            for name, value in events.action_requests.__dict__.items()
        ]
    )
    robot_events = ",".join(
        [
            name + ":" + str(value.check())
            for name, value in events.robot_async_events.__dict__.items()
        ]
    )
    mqtt_event = str(events.mqtt_queue.queue.qsize())
    upload_inspection_event = str(events.upload_inspection_event.check())
    upload_task_event = str(events.upload_task_event.check())
    return (
        api_requests
        + action_requests
        + robot_events
        + mqtt_event
        + upload_inspection_event
        + upload_task_event
    )


def test_no_state_constructor_side_effects(
    all_state_functions: dict[States, tuple[Callable, tuple]],
) -> None:
    for state_name, mapping in all_state_functions.items():
        events_hash = _get_events_hash(mapping[1][0])
        mapping[0](*mapping[1])
        assert events_hash == _get_events_hash(
            mapping[1][0]
        ), f"{state_name.name} has a side-effect in its state definition"


def test_no_empty_states(all_states_dict: dict[States, State]) -> None:
    for state_name, state_object in all_states_dict.items():
        assert (
            len(state_object.handlers) > 0
        ), f"{state_name.name} is missing eventhandlers"
