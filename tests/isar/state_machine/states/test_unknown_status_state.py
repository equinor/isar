def test_initial_unknown_status(state_machine) -> None:
    assert state_machine.state == "unknown_status"
