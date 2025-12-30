from typing import Optional, cast

from isar.eventhandlers.eventhandler import EventHandlerMapping, State
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.going_to_lockdown import GoingToLockdown
from isar.state_machine.states.lockdown import Lockdown
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states.stopping_go_to_lockdown import StoppingGoToLockdown
from robot_interface.models.mission.status import MissionStatus


def test_mission_stopped_when_going_to_lockdown(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.current_state = Monitor(sync_state_machine, "mission_id")

    monitor_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        monitor_state.get_event_handler_by_name("send_to_lockdown_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(True)

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is StoppingGoToLockdown


def test_going_to_lockdown_transitions_to_lockdown(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.current_state = GoingToLockdown(sync_state_machine)

    going_to_lockdown_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        going_to_lockdown_state.get_event_handler_by_name("mission_status_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(MissionStatus.Successful)

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is Lockdown
