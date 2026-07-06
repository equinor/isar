from typing import cast

from isar.eventhandlers.eventhandler import EventHandlerMapping, State
from isar.models.events import EmptyMessage
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.home import Home
from isar.state_machine.states.maintenance import Maintenance
from isar.state_machine.states.offline import Offline
from isar.state_machine.states.unknown_status import UnknownStatus
from robot_interface.models.mission.status import RobotStatus


def test_home_transitions_to_maintenance_mode_when_teleoperating(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Home(sync_state_machine)

    intervention_needed_state: State = cast(State, sync_state_machine.current_state)
    event_handler: EventHandlerMapping | None = (
        intervention_needed_state.get_event_handler_by_name("robot_status_event")
    )
    assert event_handler is not None

    sync_state_machine.shared_state.robot_status.trigger_event(
        RobotStatus.TeleOperation
    )

    transition = event_handler.handler(EmptyMessage())

    assert transition is not None

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is Maintenance


def test_unknown_status_transitions_to_maintenance_mode_when_teleoperating(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = UnknownStatus(sync_state_machine)

    intervention_needed_state: State = cast(State, sync_state_machine.current_state)
    event_handler: EventHandlerMapping | None = (
        intervention_needed_state.get_event_handler_by_name("robot_status_event")
    )
    assert event_handler is not None

    sync_state_machine.shared_state.robot_status.trigger_event(
        RobotStatus.TeleOperation
    )

    transition = event_handler.handler(EmptyMessage())

    assert transition is not None

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is Maintenance


def test_offline_transitions_to_maintenance_mode_when_teleoperating(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Offline(sync_state_machine)

    intervention_needed_state: State = cast(State, sync_state_machine.current_state)
    event_handler: EventHandlerMapping | None = (
        intervention_needed_state.get_event_handler_by_name("robot_status_event")
    )
    assert event_handler is not None

    sync_state_machine.shared_state.robot_status.trigger_event(
        RobotStatus.TeleOperation
    )

    transition = event_handler.handler(EmptyMessage())

    assert transition is not None

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is Maintenance
