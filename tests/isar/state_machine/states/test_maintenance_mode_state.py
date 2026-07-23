from typing import cast

from isar.models.events import Events
from isar.state_machine.state import EventHandlerMapping, State
from isar.state_machine.states.home import Home
from isar.state_machine.states.maintenance import Maintenance
from isar.state_machine.states.offline import Offline
from isar.state_machine.states.unknown_status import UnknownStatus
from robot_interface.models.mission.status import RobotStatus


def test_home_transitions_to_maintenance_mode_when_teleoperating(
    events: Events,
) -> None:
    current_state = Home(events)

    intervention_needed_state: State = cast(State, current_state)
    event_handler: EventHandlerMapping | None = (
        intervention_needed_state.get_event_handler_by_name("robot_status_event")
    )
    assert event_handler is not None

    transition = event_handler.handler(RobotStatus.TeleOperation)

    assert transition is not None

    current_state = transition(events)
    assert type(current_state) is Maintenance


def test_unknown_status_transitions_to_maintenance_mode_when_teleoperating(
    events: Events,
) -> None:
    current_state = UnknownStatus(events)

    intervention_needed_state: State = cast(State, current_state)
    event_handler: EventHandlerMapping | None = (
        intervention_needed_state.get_event_handler_by_name("robot_status_event")
    )
    assert event_handler is not None

    transition = event_handler.handler(RobotStatus.TeleOperation)

    assert transition is not None

    current_state = transition(events)
    assert type(current_state) is Maintenance


def test_offline_transitions_to_maintenance_mode_when_teleoperating(
    events: Events,
) -> None:
    current_state = Offline(events)

    intervention_needed_state: State = cast(State, current_state)
    event_handler: EventHandlerMapping | None = (
        intervention_needed_state.get_event_handler_by_name("robot_status_event")
    )
    assert event_handler is not None

    transition = event_handler.handler(RobotStatus.TeleOperation)

    assert transition is not None

    current_state = transition(events)
    assert type(current_state) is Maintenance
