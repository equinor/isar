from typing import Tuple

from isar.state_machine.states_enum import States


def mock_status(
    mission_in_progress: bool = True,
    current_state: States = States.Idle,
) -> Tuple[bool, States]:
    return mission_in_progress, current_state
