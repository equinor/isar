import logging
import time
from queue import Queue
from typing import TYPE_CHECKING

from transitions import State
from isar.models.communication.queues.queue_utils import (
    check_for_event,
    check_shared_state,
)
from isar.models.communication.queues.status_queue import StatusQueue
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class UnknownStatus(State):
    def __init__(self, state_machine: "StateMachine") -> None:
        super().__init__(name="unknown_status", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")
        self.events = self.state_machine.events
        self.shared_state = self.state_machine.shared_state

    def start(self) -> None:
        self.state_machine.update_state()
        self._run()

    def stop(self) -> None:
        return

    def _check_and_handle_stop_mission_event(self, event: Queue) -> bool:
        if check_for_event(event):
            self.state_machine.stop()  # type: ignore
            return True
        return False

    def _check_and_handle_robot_status_event(
        self, event: StatusQueue[RobotStatus]
    ) -> bool:
        robot_status: RobotStatus = check_shared_state(event)
        if robot_status == RobotStatus.Docked:
            self.state_machine.robot_docked()  # type: ignore
            return True
        elif robot_status == RobotStatus.Offline:
            self.state_machine.robot_turned_offline()  # type: ignore
            return True
        elif robot_status == RobotStatus.BlockedProtectiveStop:
            self.state_machine.robot_protective_stop_engaged()  # type: ignore
            return True
        elif robot_status == RobotStatus.Available:
            self.state_machine.robot_is_available()  # type: ignore
            return True

        return False

    def _run(self) -> None:
        while True:
            if self._check_and_handle_stop_mission_event(
                self.events.api_requests.stop_mission.input
            ):
                break

            if self._check_and_handle_robot_status_event(
                self.shared_state.robot_status
            ):
                break

            time.sleep(self.state_machine.sleep_time)
