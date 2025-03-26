from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def def_transition(
    state_machine: "StateMachine", transition_function: Callable[["StateMachine"], bool]
) -> Callable[[], bool]:
    return lambda: transition_function(state_machine)
