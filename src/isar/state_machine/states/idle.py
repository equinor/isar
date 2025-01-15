import logging
import time
from typing import TYPE_CHECKING, Optional

from transitions import State

from isar.config.settings import settings
from isar.models.communication.message import StartMissionMessage
from isar.services.utilities.threaded_request import (
    ThreadedRequest,
    ThreadedRequestNotFinishedError,
)
from robot_interface.models.exceptions.robot_exceptions import RobotException
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Idle(State):
    def __init__(self, state_machine: "StateMachine") -> None:
        super().__init__(name="idle", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")
        self.robot_status_thread: Optional[ThreadedRequest] = None
        self.last_robot_status_poll_time: float = time.time()
        self.status_checked_at_least_once: bool = False

    def start(self) -> None:
        self.state_machine.update_state()
        self._run()

    def stop(self) -> None:
        if self.robot_status_thread:
            self.robot_status_thread.wait_for_thread()
        self.robot_status_thread = None
        self.status_checked_at_least_once = False

    def _is_ready_to_poll_for_status(self) -> bool:
        if not self.status_checked_at_least_once:
            return True

        time_since_last_robot_status_poll = (
            time.time() - self.last_robot_status_poll_time
        )
        return (
            time_since_last_robot_status_poll > settings.ROBOT_API_STATUS_POLL_INTERVAL
        )

    def _run(self) -> None:
        while True:
            if self.state_machine.should_stop_mission():
                transition = self.state_machine.stop  # type: ignore
                break

            if self.status_checked_at_least_once:
                start_mission: Optional[StartMissionMessage] = (
                    self.state_machine.should_start_mission()
                )
                if start_mission:
                    self.state_machine.start_mission(
                        mission=start_mission.mission,
                        initial_pose=start_mission.initial_pose,
                    )
                    transition = self.state_machine.mission_started  # type: ignore
                    break
                time.sleep(self.state_machine.sleep_time)

            if not self._is_ready_to_poll_for_status():
                continue

            if not self.robot_status_thread:
                self.robot_status_thread = ThreadedRequest(
                    request_func=self.state_machine.robot.robot_status
                )
                self.robot_status_thread.start_thread(
                    name="State Machine Offline Get Robot Status"
                )

            try:
                robot_status: RobotStatus = self.robot_status_thread.get_output()
                self.status_checked_at_least_once = True
            except ThreadedRequestNotFinishedError:
                time.sleep(self.state_machine.sleep_time)
                continue

            except RobotException as e:
                self.logger.error(
                    f"Failed to get robot status because: {e.error_description}"
                )

            self.last_robot_status_poll_time = time.time()

            if robot_status == RobotStatus.Offline:
                transition = self.state_machine.robot_turned_offline  # type: ignore
                break
            elif robot_status == RobotStatus.BlockedProtectiveStop:
                transition = self.state_machine.robot_protective_stop_engaged  # type: ignore
                break

            self.robot_status_thread = None

        transition()
