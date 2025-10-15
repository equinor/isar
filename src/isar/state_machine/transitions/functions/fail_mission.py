from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def report_failed_return_home_and_intervention_needed(
    state_machine: "StateMachine",
) -> None:
    error_message: str = "Return home failed."
    state_machine.publish_intervention_needed(error_message=error_message)
    state_machine.print_transitions()


def report_failed_lockdown_and_intervention_needed(
    state_machine: "StateMachine",
) -> None:
    error_message: str = "Lockdown mission failed."
    state_machine.publish_intervention_needed(error_message=error_message)
