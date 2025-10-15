from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def finish_mission(state_machine: "StateMachine") -> bool:
    state_machine.print_transitions()
    return True
