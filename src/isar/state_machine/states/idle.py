import logging
import time
from typing import Optional, TYPE_CHECKING

from transitions import State

from isar.models.communication.message import StartMissionMessage

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Idle(State):
    def __init__(self, state_machine: "StateMachine") -> None:
        super().__init__(name="idle", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")

    def start(self) -> None:
        self.state_machine.update_state()
        self._run()

    def stop(self) -> None:
        pass

    def _run(self) -> None:
        while True:
            start_mission: Optional[
                StartMissionMessage
            ] = self.state_machine.should_start_mission()
            if start_mission:
                self.state_machine.start_mission(
                    mission=start_mission.mission,
                    mission_metadata=start_mission.mission_metadata,
                    initial_pose=start_mission.initial_pose,
                )
                transition = self.state_machine.mission_started  # type: ignore
                break
            time.sleep(self.state_machine.sleep_time)

        transition()
