import logging
import time
from typing import TYPE_CHECKING, Callable, Optional

from transitions import State

from isar.config.settings import settings
from isar.models.communication.message import StartMissionMessage
from isar.models.communication.queues.queue_utils import (
    check_for_event,
    check_shared_state,
)
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

    def _is_ready_to_poll_for_status(self) -> bool:
        time_since_last_robot_status_poll = (
            time.time() - self.last_robot_status_poll_time
        )
        return (
            time_since_last_robot_status_poll > settings.ROBOT_API_STATUS_POLL_INTERVAL
        )

    def _run(self) -> None:
        transition: Callable
        while True:
            if check_for_event(self.events.api_requests.api_stop_mission.input):
                transition = self.state_machine.stop  # type: ignore
                break

            start_mission: Optional[StartMissionMessage] = check_for_event(
                self.events.api_requests.api_start_mission.input
            )
            if start_mission:
                self.state_machine.start_mission(mission=start_mission.mission)
                transition = self.state_machine.request_mission_start  # type: ignore
                break

            robot_status = check_shared_state(self.shared_state.robot_status)
            if robot_status == RobotStatus.Offline:
                transition = self.state_machine.robot_turned_offline  # type: ignore
                break
            elif robot_status == RobotStatus.BlockedProtectiveStop:
                transition = self.state_machine.robot_protective_stop_engaged  # type: ignore
                break

            time.sleep(self.state_machine.sleep_time)
        transition()
