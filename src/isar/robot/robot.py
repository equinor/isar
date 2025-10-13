import logging
from queue import Queue
from threading import Event as ThreadEvent
from typing import List, Optional, Tuple

from isar.models.events import (
    Event,
    Events,
    RobotServiceEvents,
    SharedState,
    StateMachineEvents,
)
from isar.robot.robot_battery import RobotBatteryThread
from isar.robot.robot_monitor_mission import RobotMonitorMissionThread
from isar.robot.robot_pause_mission import RobotPauseMissionThread
from isar.robot.robot_start_mission import RobotStartMissionThread
from isar.robot.robot_status import RobotStatusThread
from isar.robot.robot_stop_mission import RobotStopMissionThread
from isar.robot.robot_upload_inspection import RobotUploadInspectionThread
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import TASKS
from robot_interface.robot_interface import RobotInterface
from robot_interface.telemetry.mqtt_client import MqttClientInterface


class Robot(object):
    def __init__(
        self,
        events: Events,
        robot: RobotInterface,
        shared_state: SharedState,
        mqtt_publisher: MqttClientInterface,
    ) -> None:
        self.logger = logging.getLogger("robot")
        self.state_machine_events: StateMachineEvents = events.state_machine_events
        self.robot_service_events: RobotServiceEvents = events.robot_service_events
        self.mqtt_publisher: MqttClientInterface = mqtt_publisher
        self.upload_queue: Queue = events.upload_queue
        self.shared_state: SharedState = shared_state
        self.robot: RobotInterface = robot
        self.start_mission_thread: Optional[RobotStartMissionThread] = None
        self.robot_battery_thread: Optional[RobotBatteryThread] = None
        self.robot_status_thread: Optional[RobotStatusThread] = None
        self.monitor_mission_thread: Optional[RobotMonitorMissionThread] = None
        self.stop_mission_thread: Optional[RobotStopMissionThread] = None
        self.pause_mission_thread: Optional[RobotPauseMissionThread] = None
        self.upload_inspection_threads: List[RobotUploadInspectionThread] = []
        self.signal_thread_quitting: ThreadEvent = ThreadEvent()

    def stop(self) -> None:
        self.signal_thread_quitting.set()
        if self.robot_status_thread is not None and self.robot_status_thread.is_alive():
            self.robot_status_thread.join()
        if (
            self.robot_battery_thread is not None
            and self.robot_battery_thread.is_alive()
        ):
            self.robot_battery_thread.join()
        if (
            self.monitor_mission_thread is not None
            and self.monitor_mission_thread.is_alive()
        ):
            self.monitor_mission_thread.join()
        if (
            self.start_mission_thread is not None
            and self.start_mission_thread.is_alive()
        ):
            self.start_mission_thread.join()
        if self.stop_mission_thread is not None and self.stop_mission_thread.is_alive():
            self.stop_mission_thread.join()
        self.robot_status_thread = None
        self.robot_battery_thread = None
        self.start_mission_thread = None
        self.monitor_mission_thread = None

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
            if (
                self.monitor_mission_thread is not None
                and self.monitor_mission_thread.is_alive()
            ):
                self.logger.warning(
                    "Attempted to start mission while monitoring an old mission."
                )
                self.monitor_mission_thread.join()

            self.start_mission_thread = RobotStartMissionThread(
                self.robot_service_events,
                self.robot,
                self.signal_thread_quitting,
                start_mission,
            )
            self.monitor_mission_thread = RobotMonitorMissionThread(
                self.robot_service_events,
                self.shared_state,
                self.robot,
                self.mqtt_publisher,
                self.signal_thread_quitting,
                start_mission,
            )
            self.start_mission_thread.start()
            self.monitor_mission_thread.start()

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

    def _pause_mission_request_handler(self, event: Event[bool]) -> None:
        if event.consume_event():
            if (
                self.pause_mission_thread is not None
                and self.pause_mission_thread.is_alive()
            ):
                self.logger.warning(
                    "Received pause mission event while trying to pause a mission. Aborting pause attempt."
                )
                return
            if (
                self.start_mission_thread is not None
                and self.start_mission_thread.is_alive()
            ):
                error_description = "Received pause mission event while trying to start a mission. Aborting pause attempt."
                error_message = ErrorMessage(
                    error_reason=ErrorReason.RobotStillStartingMissionException,
                    error_description=error_description,
                )
                self.robot_service_events.mission_failed_to_stop.trigger_event(
                    error_message
                )
                return
            self.pause_mission_thread = RobotPauseMissionThread(
                self.robot_service_events, self.robot, self.signal_thread_quitting
            )
            self.pause_mission_thread.start()

    def _upload_inspection_event_handler(
        self, event: Event[Tuple[TASKS, Mission]]
    ) -> None:
        upload_request = event.consume_event()
        if upload_request:

            upload_inspection_thread = RobotUploadInspectionThread(
                self.upload_queue, self.robot, upload_request[0], upload_request[1]
            )
            self.upload_inspection_threads.append(upload_inspection_thread)
            upload_inspection_thread.start()

        def _join_threads(thread: RobotUploadInspectionThread) -> bool:
            if thread.is_done():
                thread.join()
                return True
            return False

        self.upload_inspection_threads[:] = [
            thread for thread in self.upload_inspection_threads if _join_threads(thread)
        ]

    def run(self) -> None:
        self.robot_status_thread = RobotStatusThread(
            robot=self.robot,
            signal_thread_quitting=self.signal_thread_quitting,
            shared_state=self.shared_state,
            state_machine_events=self.state_machine_events,
            robot_service_events=self.robot_service_events,
        )
        self.robot_status_thread.start()

        self.robot_battery_thread = RobotBatteryThread(
            self.robot, self.signal_thread_quitting, self.shared_state
        )
        self.robot_battery_thread.start()

        while not self.signal_thread_quitting.wait(0):
            self._start_mission_event_handler(self.state_machine_events.start_mission)

            self._pause_mission_request_handler(self.state_machine_events.pause_mission)

            self._stop_mission_request_handler(self.state_machine_events.stop_mission)

            self._upload_inspection_event_handler(
                self.robot_service_events.request_inspection_upload
            )

        self.logger.info("Exiting robot service main thread")
