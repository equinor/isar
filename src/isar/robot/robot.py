import logging
from queue import Queue
from threading import Event
from typing import Optional

from dependency_injector.wiring import inject

from isar.models.communication.queues.events import (
    Events,
    RobotServiceEvents,
    SharedState,
    StateMachineEvents,
)
from isar.models.communication.queues.queue_utils import check_for_event, trigger_event
from isar.robot.robot_start_mission import RobotStartMissionThread
from isar.robot.robot_status import RobotStatusThread
from isar.robot.robot_stop_mission import RobotStopMissionThread
from isar.robot.robot_task_status import RobotTaskStatusThread
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.robot_interface import RobotInterface


class Robot(object):
    @inject
    def __init__(
        self, events: Events, robot: RobotInterface, shared_state: SharedState
    ) -> None:
        self.logger = logging.getLogger("robot")
        self.state_machine_events: StateMachineEvents = events.state_machine_events
        self.robot_service_events: RobotServiceEvents = events.robot_service_events
        self.shared_state: SharedState = shared_state
        self.robot: RobotInterface = robot
        self.start_mission_thread: Optional[RobotStartMissionThread] = None
        self.robot_status_thread: Optional[RobotStatusThread] = None
        self.robot_task_status_thread: Optional[RobotTaskStatusThread] = None
        self.stop_mission_thread_thread: Optional[RobotStopMissionThread] = None
        self.signal_thread_quitting: Event = Event()

    def stop(self) -> None:
        self.signal_thread_quitting.set()
        if self.robot_status_thread is not None and self.robot_status_thread.is_alive():
            self.robot_status_thread.join()
        if (
            self.robot_task_status_thread is not None
            and self.robot_status_thread.is_alive()
        ):
            self.robot_task_status_thread.join()
        if (
            self.start_mission_thread is not None
            and self.robot_status_thread.is_alive()
        ):
            self.start_mission_thread.join()
        if (
            self.stop_mission_thread_thread is not None
            and self.stop_mission_thread_thread.is_alive()
        ):
            self.stop_mission_thread_thread.join()
        self.robot_status_thread = None
        self.robot_task_status_thread = None
        self.start_mission_thread = None

    def _check_and_handle_start_mission(self, event: Queue) -> None:
        start_mission = check_for_event(event)
        if start_mission is not None:
            if (
                self.start_mission_thread is not None
                and self.start_mission_thread.is_alive()
            ):
                self.logger.warning(
                    "Attempted to start mission while another mission was starting."
                )
                self.start_mission_thread.join()
            self.start_mission_thread = RobotStartMissionThread(
                self.robot_service_events,
                self.robot,
                self.signal_thread_quitting,
                start_mission,
            )
            self.start_mission_thread.start()

    def _check_and_handle_task_status_request(self, event: Queue[str]) -> None:
        task_id: str = check_for_event(event)
        if task_id:
            self.robot_task_status_thread = RobotTaskStatusThread(
                self.robot_service_events,
                self.robot,
                self.signal_thread_quitting,
                task_id,
            )
            self.robot_task_status_thread.start()

    def _check_and_handle_stop_mission(self, event: Queue) -> None:
        if check_for_event(event):
            if (
                self.stop_mission_thread_thread is not None
                and self.start_mission_thread.is_alive()
            ):
                error_description = "Received stop mission event while trying to start a mission. Aborting stop attempt."
                error_message = ErrorMessage(
                    error_reason=ErrorReason.RobotStillStartingMissionException,
                    error_description=error_description,
                )
                trigger_event(
                    self.robot_service_events.mission_failed_to_stop, error_message
                )
                return
            self.stop_mission_thread_thread = RobotStopMissionThread(
                self.robot_service_events, self.robot, self.signal_thread_quitting
            )
            self.stop_mission_thread_thread.start()

    def run(self) -> None:
        self.robot_status_thread = RobotStatusThread(
            self.robot, self.signal_thread_quitting, self.shared_state
        )
        self.robot_status_thread.start()

        while not self.signal_thread_quitting.wait(0):
            self._check_and_handle_start_mission(
                self.state_machine_events.start_mission
            )

            self._check_and_handle_task_status_request(
                self.state_machine_events.task_status_request
            )

            self._check_and_handle_stop_mission(self.state_machine_events.stop_mission)

        self.logger.info("Exiting robot service main thread")
