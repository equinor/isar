import logging
import time
from typing import TYPE_CHECKING

from transitions import State

from isar.services.utilities.threaded_request import (
    ThreadedRequest,
    ThreadedRequestNotFinishedError,
    ThreadedRequestUnexpectedError,
)
from isar.state_machine.states_enum import States
from robot_interface.models.mission import Step, TakeImage, TakeThermalImage

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Send(State):
    def __init__(self, state_machine: "StateMachine"):
        super().__init__(name="send", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.send_failure_counter = 0
        self.send_failure_counter_limit = 10
        self.logger = logging.getLogger("state_machine")

        self.send_thread = None

    def start(self):
        self.state_machine.update_status()
        self.logger.info(f"State: {self.state_machine.status.current_state}")

        self._run()

    def stop(self):
        self.send_failure_counter = 0
        if self.send_thread:
            self.send_thread.wait_for_thread()
        self.send_thread = None

    def _run(self):
        while True:
            if self.state_machine.should_stop():
                self.state_machine.stop_mission()

            if not self.state_machine.status.mission_in_progress:
                next_state: States = States.Cancel
                break

            if not self.state_machine.status.mission_schedule.mission_steps:
                next_state: States = States.Cancel
                break

            if self.state_machine.should_send_status():
                self.state_machine.send_status()

            if not self.send_thread:
                self.state_machine.status.current_mission_step = (
                    self._get_current_mission()
                )
                self.send_thread = ThreadedRequest(
                    self.state_machine.robot.schedule_step
                )
                self.send_thread.start_thread(
                    self.state_machine.status.current_mission_step
                )
            try:
                (
                    send_success,
                    mission_instance_id,
                    computed_joints,
                ) = self.send_thread.get_output()
            except ThreadedRequestNotFinishedError:
                time.sleep(self.state_machine.sleep_time)
                continue
            except ThreadedRequestUnexpectedError:
                send_success = False
                mission_instance_id = None
                computed_joints = None

            if send_success:
                self.state_machine.status.current_mission_instance_id = (
                    mission_instance_id
                )
                if isinstance(
                    self.state_machine.status.current_mission_step,
                    (TakeImage, TakeThermalImage),
                ):
                    self.state_machine.status.current_mission_step.computed_joints = (
                        computed_joints
                    )
                self.state_machine.status.mission_schedule.mission_steps.pop(0)
                next_state = States.Monitor
                break
            else:
                self.send_failure_counter += 1
                self.logger.info("sending failed #: " + str(self.send_failure_counter))
                if self.send_failure_counter >= self.send_failure_counter_limit:
                    self.logger.error(
                        f"Failed to send mission after "
                        f"{self.send_failure_counter_limit} attempts. "
                        f"Cancelling mission."
                    )
                    next_state: States = States.Cancel
                    break
                self.send_thread = None
                time.sleep(self.state_machine.sleep_time)

        self.state_machine.to_next_state(next_state)

    def _get_current_mission(self) -> Step:
        return self.state_machine.status.mission_schedule.mission_steps[0]
