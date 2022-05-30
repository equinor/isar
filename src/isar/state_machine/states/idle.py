import logging
import time
from typing import TYPE_CHECKING, Optional

from transitions import State

from isar.models.communication.message import StartMissionMessage

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Idle(State):
    def __init__(self, state_machine: "StateMachine"):
        super().__init__(name="idle", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")

    def start(self):
        self.state_machine.update_state()
        self._run()

    def stop(self):
        pass

    def _run(self):
        while True:
            start_mission: Optional[
                StartMissionMessage
            ] = self.state_machine.should_start_mission()
            if start_mission:
                self.state_machine.start_mission(
                    mission=start_mission.mission,
                    initial_pose=start_mission.initial_pose,
                )
                transition = self.state_machine.mission_started
                break
            time.sleep(self.state_machine.sleep_time)

        transition()
