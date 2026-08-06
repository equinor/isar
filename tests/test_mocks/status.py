from isar.state_machine.states_enum import States


def stub_status(
    mission_in_progress: bool = True,
    current_state: States = States.Home,
) -> tuple[bool, States]:
    return mission_in_progress, current_state
