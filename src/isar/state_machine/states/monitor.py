import logging
import time
from typing import TYPE_CHECKING

from injector import inject
from transitions import State

from isar.state_machine.states_enum import States
from robot_interface.models.mission import DriveToPose, MissionStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Monitor(State):
    @inject
    def __init__(self, state_machine: "StateMachine"):
        super().__init__(name="monitor", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")

        self.iteration_counter: int = 0
        self.log_interval = 10

    def start(self):
        self.state_machine.update_status()
        self.logger.info(f"State: {self.state_machine.status.current_state}")

        self._run()

    def stop(self):
        self.iteration_counter = 0

    def _run(self):
        while True:
            if self.state_machine.should_stop():
                self.state_machine.stop_mission()

            if not self.state_machine.status.mission_in_progress:
                next_state = States.Cancel
                break

            mission_status: MissionStatus = self.state_machine.robot.mission_status(
                self.state_machine.status.current_mission_instance_id
            )
            self.state_machine.status.mission_status = mission_status
            self._log_status(mission_status=mission_status)

            if self._mission_finished(
                mission_status=mission_status,
                instance_id=self.state_machine.status.current_mission_instance_id,
            ):
                if isinstance(
                    self.state_machine.status.current_mission_step, DriveToPose
                ):
                    next_state = States.Send
                else:
                    next_state = States.Collect
                break

            if self.state_machine.should_send_status():
                self.state_machine.send_status()
            time.sleep(self.state_machine.sleep_time)

        self.state_machine.to_next_state(next_state)

    def _mission_finished(
        self, mission_status: MissionStatus, instance_id: int
    ) -> bool:
        if mission_status == MissionStatus.Unexpected:
            self.logger.error(
                f"Mission status on step {instance_id} returned and unexpected status string"
            )
        elif mission_status == MissionStatus.Failed:
            self.logger.warning(f"Mission instance {instance_id} failed...")
            return True
        elif mission_status == MissionStatus.Completed:
            return True
        return False

    def _log_status(self, mission_status: MissionStatus):
        if self.iteration_counter % self.log_interval == 0:
            self.state_machine.robot.log_status(
                mission_id=self.state_machine.status.current_mission_instance_id,
                mission_status=mission_status,
                current_step=self.state_machine.status.current_mission_step,
            )
        self.iteration_counter += 1
