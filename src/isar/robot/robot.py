import logging
from threading import Event as ThreadEvent
from typing import Optional

from isar.models.events import (
    Event,
    Events,
    RobotServiceEvents,
    SharedState,
    StateMachineEvents,
)
from isar.robot.robot_start_mission import RobotStartMissionThread
from isar.robot.robot_status import RobotStatusThread
from isar.robot.robot_stop_mission import RobotStopMissionThread
from isar.robot.robot_task_status import RobotTaskStatusThread
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.mission import Mission
from robot_interface.robot_interface import RobotInterface


class Robot(object):
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
        self.stop_mission_thread: Optional[RobotStopMissionThread] = None
        self.signal_thread_quitting: ThreadEvent = ThreadEvent()

    def stop(self) -> None:
        self.signal_thread_quitting.set()
        if self.robot_status_thread is not None and self.robot_status_thread.is_alive():
            self.robot_status_thread.join()
        if (
            self.robot_task_status_thread is not None
            and self.robot_task_status_thread.is_alive()
        ):
            self.robot_task_status_thread.join()
        if (
            self.start_mission_thread is not None
            and self.start_mission_thread.is_alive()
        ):
            self.start_mission_thread.join()
        if self.stop_mission_thread is not None and self.stop_mission_thread.is_alive():
            self.stop_mission_thread.join()
        self.robot_status_thread = None
        self.robot_task_status_thread = None
        self.start_mission_thread = None

    def _start_mission_event_handler(self, event: Event[Mission]) -> None:
        start_mission = event.consume_event()
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

    def _task_status_request_handler(self, event: Event[str]) -> None:
        task_id: str = event.consume_event()
        if task_id:
            self.robot_task_status_thread = RobotTaskStatusThread(
                self.robot_service_events,
                self.robot,
                self.signal_thread_quitting,
                task_id,
            )
            self.robot_task_status_thread.start()

    def _stop_mission_request_handler(self, event: Event[bool]) -> None:
        if event.consume_event():
            if (
                self.stop_mission_thread is not None
                and self.stop_mission_thread.is_alive()
            ):
                self.logger.warning(
                    "Received stop mission event while trying to stop a mission. Aborting stop attempt."
                )
                return
            if (
                self.start_mission_thread is not None
                and self.start_mission_thread.is_alive()
            ):
                error_description = "Received stop mission event while trying to start a mission. Aborting stop attempt."
                error_message = ErrorMessage(
                    error_reason=ErrorReason.RobotStillStartingMissionException,
                    error_description=error_description,
                )
                self.robot_service_events.mission_failed_to_stop.trigger_event(
                    error_message
                )
                return
            self.stop_mission_thread = RobotStopMissionThread(
                self.robot_service_events, self.robot, self.signal_thread_quitting
            )
            self.stop_mission_thread.start()

    def run(self) -> None:
        self.robot_status_thread = RobotStatusThread(
            self.robot, self.signal_thread_quitting, self.shared_state
        )
        self.robot_status_thread.start()

        while not self.signal_thread_quitting.wait(0):
            self._start_mission_event_handler(self.state_machine_events.start_mission)

            self._task_status_request_handler(
                self.state_machine_events.task_status_request
            )

            self._stop_mission_request_handler(self.state_machine_events.stop_mission)

        self.logger.info("Exiting robot service main thread")
