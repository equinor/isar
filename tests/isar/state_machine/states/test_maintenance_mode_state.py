from isar.models.events import Events
from isar.state_machine.state import EventHandlerMapping
from isar.state_machine.states.home import Home
from isar.state_machine.states.offline import Offline
from isar.state_machine.states.unknown_status import UnknownStatus
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import RobotStatus


def test_home_transitions_to_maintenance_mode_when_teleoperating(
    events: Events,
) -> None:
    current_state = Home(events)

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.robot_service_events.robot_status_update
    )

    transition = event_handler.handler(RobotStatus.TeleOperation)

    assert transition is not None

    current_state = transition(events)
    assert current_state.name is States.Maintenance


def test_unknown_status_transitions_to_maintenance_mode_when_teleoperating(
    events: Events,
) -> None:
    current_state = UnknownStatus(events)

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.robot_service_events.robot_status_update
    )

    transition = event_handler.handler(RobotStatus.TeleOperation)

    assert transition is not None

    current_state = transition(events)
    assert current_state.name is States.Maintenance


def test_offline_transitions_to_maintenance_mode_when_teleoperating(
    events: Events,
) -> None:
    current_state = Offline(events)

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.robot_service_events.robot_status_update
    )

    transition = event_handler.handler(RobotStatus.TeleOperation)

    assert transition is not None

    current_state = transition(events)
    assert current_state.name is States.Maintenance
