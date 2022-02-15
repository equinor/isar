import logging
from typing import TYPE_CHECKING

from injector import inject
from transitions import State

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Finalize(State):
    @inject
    def __init__(self, state_machine: "StateMachine"):
        super().__init__(name="finalize", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")

    def start(self):
        self.state_machine.update_state()

        self.state_machine.log_task_overview(mission=self.state_machine.current_mission)
        next_state = self.state_machine.reset_state_machine()
        self.state_machine.to_next_state(next_state)

    def stop(self):
        self._log_state_transitions()

    def _log_state_transitions(self):
        state_transitions: str = ", ".join(
            [
                f"\n  {transition}" if (i + 1) % 10 == 0 else f"{transition}"
                for i, transition in enumerate(
                    list(self.state_machine.transitions_list)
                )
            ]
        )

        self.logger.info(f"State transitions:\n  {state_transitions}")
