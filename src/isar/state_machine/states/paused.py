import logging
import time
from typing import TYPE_CHECKING, Callable, Optional

from transitions import State

from isar.config.settings import RobotSettings
from isar.services.utilities.threaded_request import ThreadedRequest

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Paused(State):
    def __init__(self, state_machine: "StateMachine") -> None:
        super().__init__(name="paused", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")
        self.resume_mission_thread: Optional[ThreadedRequest] = None

    def start(self) -> None:
        self.state_machine.update_state()
        self._run()

    def stop(self) -> None:
        if self.resume_mission_thread:
            self.resume_mission_thread.wait_for_thread()
        self.resume_mission_thread = None

    def _run(self) -> None:
        transition: Callable
        while True:
            if self.state_machine.should_stop_mission():
                transition = self.state_machine.mission_stopped  # type: ignore
                break

            if self.state_machine.should_resume_mission():
                transition = self.state_machine.resume  # type: ignore
                if "pause_mission" in RobotSettings.CAPABILITIES:
                    self._run_resume_mission_thread(
                        resume_mission_function=self.state_machine.robot.resume,
                        thread_name="State Machine Paused Resume Mission",
                    )
                break

            time.sleep(self.state_machine.sleep_time)

        transition()

    def _run_resume_mission_thread(
        self, resume_mission_function: Callable, thread_name: str
    ) -> None:
        self.resume_mission_thread = ThreadedRequest(
            request_func=resume_mission_function
        )
        self.resume_mission_thread.start_thread(name=thread_name)
