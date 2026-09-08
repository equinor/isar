from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states_enum import States


def test_initial_unknown_status(state_machine: StateMachine) -> None:
    assert state_machine.current_state.name == States.UnknownStatus
