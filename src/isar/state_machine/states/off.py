import logging
from typing import TYPE_CHECKING

from transitions import State

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Off(State):
    def __init__(self, state_machine: "StateMachine"):
        super().__init__(name="off", on_enter=self.start)
        self.logger = logging.getLogger("state_machine")
        self.state_machine: "StateMachine" = state_machine

    def start(self):
        self.state_machine.update_status()
        self.logger.info(f"State: {self.state_machine.current_state}")
