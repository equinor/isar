import logging
import time
from typing import Callable, TYPE_CHECKING

from transitions import State

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Paused(State):
    def __init__(self, state_machine: "StateMachine") -> None:
        super().__init__(name="paused", on_enter=self.start)
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")

    def start(self) -> None:
        self.state_machine.update_state()
        self._run()

    def _run(self) -> None:
        transition: Callable
        while True:
            if self.state_machine.should_stop_mission():
                transition = self.state_machine.mission_stopped  # type: ignore
                break

            if self.state_machine.should_resume_mission():
                if self.state_machine.run_mission_by_task:
                    transition = self.state_machine.resume  # type: ignore
                else:
                    transition = self.state_machine.resume_full_mission  # type: ignore
                break

            time.sleep(self.state_machine.sleep_time)

        transition()
