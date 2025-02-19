import logging
import time
from typing import TYPE_CHECKING, Optional

from transitions import State

from isar.config.settings import settings
from isar.models.communication.message import StartMissionMessage

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class AwaitNextMission(State):
    def __init__(self, state_machine: "StateMachine") -> None:
        super().__init__(
            name="await_next_mission", on_enter=self.start, on_exit=self.stop
        )
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")
        self.entered_time: float = time.time()
        self.return_home_delay: float = settings.RETURN_HOME_DELAY

    def start(self) -> None:
        self.state_machine.update_state()
        self.entered_time = time.time()
        self._run()

    def stop(self) -> None:
        pass

    def _should_return_home(self) -> bool:
        time_since_entered = time.time() - self.entered_time
        return time_since_entered > self.return_home_delay

    def _run(self) -> None:
        while True:
            if self.state_machine.should_stop_mission():
                transition = self.state_machine.stop  # type: ignore
                break

            start_mission: Optional[StartMissionMessage] = (
                self.state_machine.should_start_mission()
            )
            if start_mission:
                self.state_machine.start_mission(mission=start_mission.mission)
                transition = self.state_machine.mission_started  # type: ignore
                break

            if self._should_return_home():
                transition = self.state_machine.return_home  # type: ignore
                break

            time.sleep(self.state_machine.sleep_time)

        transition()
