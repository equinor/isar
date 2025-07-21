import logging
import time
from enum import Enum
from queue import Queue
from typing import TYPE_CHECKING, Optional

from isar.config.settings import settings
from isar.models.communication.message import StartMissionMessage
from isar.models.communication.queues.queue_io import QueueIO
from isar.models.communication.queues.queue_utils import (
    check_for_event,
    check_shared_state,
)
from isar.models.communication.queues.status_queue import StatusQueue
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class IdleStates(str, Enum):
    AwaitNextMission = "awaitNextMission"
    Home = "home"
    RobotStandingStill = "robotStandingStill"


if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Idle:
    def __init__(
        self,
        state_machine: "StateMachine",
        state: IdleStates,
    ) -> None:
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")
        self.events = state_machine.events
        self.shared_state = self.state_machine.shared_state
        self.signal_state_machine_to_stop = state_machine.signal_state_machine_to_stop
        self.state: IdleStates = state

        # Only used for await_next_mission state
        self.entered_time: float = time.time()
        self.return_home_delay: float = settings.RETURN_HOME_DELAY

    def start(self) -> None:
        self.state_machine.update_state()
        self.entered_time = time.time()
        self._run()

    def stop(self) -> None:
        return

    def _check_and_handle_start_mission_event(
        self, event: Queue[StartMissionMessage]
    ) -> bool:
        start_mission: Optional[StartMissionMessage] = check_for_event(event)
        if start_mission:
            self.state_machine.start_mission(mission=start_mission.mission)
            self.state_machine.request_mission_start()  # type: ignore
            return True
        return False

    def _check_and_handle_return_home_event(self, event: QueueIO) -> bool:
        if check_for_event(event.input):
            event.output.put(True)
            self.state_machine.request_return_home()  # type: ignore
            return True
        return False

    def _check_and_handle_robot_status_event(
        self, event: StatusQueue[RobotStatus]
    ) -> bool:
        robot_status: RobotStatus = check_shared_state(event)

        expected_robot_status = (
            RobotStatus.Home if self.state == IdleStates.Home else RobotStatus.Available
        )

        if robot_status != expected_robot_status:
            self.state_machine.robot_status_changed()  # type: ignore
            return True

        return False

    def _check_and_handle_stop_mission_event(self, event: Queue) -> bool:
        if check_for_event(event) is not None:
            self.state_machine.stop()  # type: ignore
            return True
        return False

    def _should_return_home(self) -> bool:
        time_since_entered = time.time() - self.entered_time
        return time_since_entered > self.return_home_delay

    def _run(self) -> None:
        while True:
            if self.signal_state_machine_to_stop.is_set():
                self.logger.info(
                    "Stopping state machine from %s state", self.state.name
                )
                break

            if self._check_and_handle_stop_mission_event(
                self.events.api_requests.stop_mission.input
            ):
                break

            if self._check_and_handle_start_mission_event(
                self.events.api_requests.start_mission.input
            ):
                break

            if self._check_and_handle_return_home_event(
                self.events.api_requests.return_home
            ):
                break

            if (
                self.state != IdleStates.AwaitNextMission
                and self._check_and_handle_robot_status_event(
                    self.shared_state.robot_status
                )
            ):
                break

            if self.state == IdleStates.AwaitNextMission and self._should_return_home():
                self.state_machine.request_return_home()  # type: ignore
                break

            time.sleep(self.state_machine.sleep_time)
