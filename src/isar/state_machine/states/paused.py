import logging
import time
from typing import TYPE_CHECKING, Callable

from transitions import State

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Paused(State):
    def __init__(self, state_machine: "StateMachine"):
        super().__init__(name="paused", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")

    def start(self):
        self.state_machine.update_state()
        self._run()

    def stop(self):
        self.state_machine.paused = False

    def _run(self):
        transition: Callable
        while True:
            if self.state_machine.should_stop_mission():
                transition = self.state_machine.mission_stopped
                break

            if self.state_machine.should_continue_mission():
                transition = self.state_machine.unpause
                break

            if self.state_machine.should_send_status():
                self.state_machine.send_status()

            time.sleep(self.state_machine.sleep_time)

        transition()
