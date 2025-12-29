from isar.state_machine.states_enum import States


def test_initial_unknown_status(state_machine) -> None:
    assert state_machine.current_state.name == States.UnknownStatus
