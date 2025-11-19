from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def trigger_stop_mission_event(state_machine: "StateMachine") -> bool:
    state_machine.events.state_machine_events.stop_mission.trigger_event(True)
    return True
