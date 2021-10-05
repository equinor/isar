import pytest
from models.enums.states import States


@pytest.mark.parametrize(
    "expected_state",
    [States.Idle],
)
def test_reset_state_machine(state_machine, expected_state):
    next_state = state_machine.reset_state_machine()
    assert next_state is expected_state
