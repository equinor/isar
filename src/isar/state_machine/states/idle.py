import logging
import time
from typing import TYPE_CHECKING

from transitions import State

from isar.state_machine.states_enum import States

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Idle(State):
    def __init__(self, state_machine: "StateMachine"):
        super().__init__(name="idle", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")

    def start(self):
        time.sleep(self.state_machine.sleep_time)

        self.state_machine.update_status()
        self.logger.info(f"State: {self.state_machine.current_state}")

        self._run()

    def stop(self):
        pass

    def _run(self):
        while True:
            time.sleep(self.state_machine.sleep_time)
            if self.state_machine.should_stop_mission():
                self.state_machine.stop_mission()

            next_state: States = self._get_next_state()
            if not next_state == States.Idle:
                break

        self.state_machine.to_next_state(next_state)

    def _get_next_state(self) -> States:
        (should_start_mission, mission) = self.state_machine.should_start_mission()
        if should_start_mission:
            self.state_machine.start_mission(mission)
            return States.Send

        if self.state_machine.should_send_status():
            self.state_machine.send_status()

        return States.Idle
