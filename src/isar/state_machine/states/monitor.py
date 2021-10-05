import logging
import time
from typing import TYPE_CHECKING

from injector import inject
from models.enums.mission_status import MissionStatus
from models.enums.states import States
from models.planning.step import DriveToPose
from transitions import State

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Monitor(State):
    @inject
    def __init__(self, state_machine: "StateMachine"):
        super().__init__(name="monitor", on_enter=self.start)
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")

        self.iteration_counter: int = 0
        self.log_interval = 10

    def start(self):
        self.state_machine.update_status()
        self.logger.info(f"State: {self.state_machine.status.current_state}")

        next_state = self.monitor_mission()
        self.state_machine.to_next_state(next_state)

    def monitor_mission(self) -> States:
        if self.state_machine.should_stop():
            self.iteration_counter = 0
            self.state_machine.stop_mission()

        if not self.state_machine.status.mission_in_progress:
            self.iteration_counter = 0
            return States.Cancel

        mission_status: MissionStatus = self.state_machine.scheduler.mission_status(
            self.state_machine.status.current_mission_instance_id
        )
        self.state_machine.status.mission_status = mission_status

        self.log_status(mission_status=mission_status)

        if self.mission_finished(
            mission_status=mission_status,
            instance_id=self.state_machine.status.current_mission_instance_id,
        ):
            self.iteration_counter = 0
            if isinstance(self.state_machine.status.current_mission_step, DriveToPose):
                return States.Send
            return States.Collect

        if self.state_machine.should_send_status():
            self.state_machine.send_status()

        time.sleep(self.state_machine.sleep_time)

        return States.Monitor

    def mission_finished(self, mission_status: MissionStatus, instance_id: int) -> bool:
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

    def log_status(self, mission_status: MissionStatus):
        if self.iteration_counter % self.log_interval == 0:
            self.state_machine.scheduler.log_status(
                mission_id=self.state_machine.status.current_mission_instance_id,
                mission_status=mission_status,
                current_step=self.state_machine.status.current_mission_step,
            )
        self.iteration_counter += 1
