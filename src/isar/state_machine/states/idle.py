import logging
import time
from queue import Queue
from typing import TYPE_CHECKING, Optional

from transitions import State

from isar.models.communication.message import StartMissionMessage
from isar.models.communication.queues.queue_utils import (
    check_for_event,
    check_shared_state,
)
from isar.models.communication.queues.status_queue import StatusQueue
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Idle(State):
    def __init__(self, state_machine: "StateMachine") -> None:
        super().__init__(name="idle", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")
        self.last_robot_status_poll_time: float = time.time()
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

    def _check_and_handle_start_mission_event(
        self, event: Queue[StartMissionMessage]
    ) -> bool:
        start_mission: Optional[StartMissionMessage] = check_for_event(event)
        if start_mission:
            self.state_machine.start_mission(mission=start_mission.mission)
            self.state_machine.request_mission_start()  # type: ignore
            return True
        return False

    def _check_and_handle_robot_status_event(
        self, event: StatusQueue[RobotStatus]
    ) -> bool:
        robot_status: RobotStatus = check_shared_state(event)
        if robot_status == RobotStatus.Offline:
            self.state_machine.robot_turned_offline()  # type: ignore
            return True
        elif robot_status == RobotStatus.BlockedProtectiveStop:
            self.state_machine.robot_protective_stop_engaged()  # type: ignore
            return True
        return False

    def _run(self) -> None:
        while True:
            if self._check_and_handle_stop_mission_event(
                self.events.api_requests.stop_mission.input
            ):
                break

            if self._check_and_handle_start_mission_event(
                self.events.api_requests.start_mission.input
            ):
                break

            if self._check_and_handle_robot_status_event(
                self.shared_state.robot_status
            ):
                break

            time.sleep(self.state_machine.sleep_time)
