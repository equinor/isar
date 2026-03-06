import logging
from queue import Queue
from threading import Event as ThreadEvent
from threading import Thread
from typing import Callable, List, Optional, Tuple

from isar.config.settings import settings
from isar.models.events import (
    EmptyMessage,
    Events,
    RobotServiceEvents,
    SharedState,
    StateMachineEvents,
)
from isar.robot.function_thread import FunctionThread
from isar.robot.robot_battery import RobotBatteryThread
from isar.robot.robot_monitor_mission import RobotMonitorMissionThread
from isar.robot.robot_pause_mission import robot_pause_mission
from isar.robot.robot_resume_mission import robot_resume_mission
from isar.robot.robot_start_mission import robot_start_mission
from isar.robot.robot_status import RobotStatusThread
from isar.robot.robot_stop_mission import robot_stop_mission
from isar.robot.robot_upload_inspection import robot_upload_inspection
from isar.services.utilities.mqtt_utilities import publish_mission_status
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus
from robot_interface.models.mission.task import InspectionTask
from robot_interface.robot_interface import RobotInterface
from robot_interface.telemetry.mqtt_client import MqttClientInterface


class RobotService:
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
        self.action_thread: Optional[FunctionThread] = None
        self.battery_thread: Optional[RobotBatteryThread] = None
        self.status_thread: Optional[RobotStatusThread] = None
        self.monitor_mission_thread: Optional[RobotMonitorMissionThread] = None
        self.upload_inspection_threads: List[FunctionThread] = []
        self.signal_exit: ThreadEvent = ThreadEvent()
        self.signal_mission_stopped: ThreadEvent = ThreadEvent()
        self.inspection_callback_thread: Optional[Thread] = None

    def stop(self) -> None:
        self.signal_exit.set()
        if self.status_thread is not None and self.status_thread.is_alive():
            self.status_thread.join()
        if self.battery_thread is not None and self.battery_thread.is_alive():
            self.battery_thread.join()
        if (
            self.monitor_mission_thread is not None
            and self.monitor_mission_thread.is_alive()
        ):
            self.monitor_mission_thread.join()
        if self.action_thread is not None and self.action_thread.is_alive():
            self.action_thread.join()
        for thread in self.upload_inspection_threads:
            if thread.is_alive():
                thread.join()
        self.upload_inspection_threads = []
        self.status_thread = None
        self.battery_thread = None
        self.action_thread = None
        self.monitor_mission_thread = None

    def _start_mission_handler(self, mission: Mission) -> None:
        mission.status = MissionStatus.NotStarted
        publish_mission_status(self.mqtt_publisher, mission.id, mission.status, None)
        error_message: ErrorMessage | None = robot_start_mission(
            self.signal_exit, self.robot, self.logger, mission
        )

        if (
            error_message
            and error_message.error_reason == ErrorReason.RobotAlreadyHomeException
        ):
            self.robot_service_events.robot_already_home.trigger_event(EmptyMessage())
            return
        elif error_message:
            mission.status = MissionStatus.Failed
            error_message.error_description = (
                f"Failed to initiate due to: {error_message.error_description}"
            )
            mission.error_message = error_message
            publish_mission_status(
                self.mqtt_publisher, mission.id, mission.status, error_message
            )
            self.robot_service_events.mission_failed.trigger_event(error_message)
            return

        self.logger.info("Received confirmation that mission has started")

        if (
            self.monitor_mission_thread is not None
            and self.monitor_mission_thread.is_alive()
        ):
            self.logger.warning(
                "Attempted to start mission while monitoring an old mission."
            )
            # Here we panic

        self.signal_mission_stopped.clear()
        self.robot_service_events.mission_started.trigger_event(mission)

    def _stop_mission_handler(self) -> None:
        error_message: ErrorMessage | None = robot_stop_mission(
            self.signal_exit, self.robot, self.logger
        )

        if error_message:
            self.robot_service_events.mission_failed_to_stop.trigger_event(
                error_message
            )
        else:
            if (
                self.monitor_mission_thread is not None
                and self.monitor_mission_thread.is_alive()
            ):
                self.signal_mission_stopped.set()
                self.monitor_mission_thread.join()
                self.monitor_mission_thread = None

            # The mission status will already be reported on MQTT, the state machine does not need the event
            self.robot_service_events.mission_succeeded.clear_event()
            self.robot_service_events.mission_failed.clear_event()
            self.robot_service_events.mission_successfully_stopped.trigger_event(
                EmptyMessage()
            )

    def _pause_mission_handler(self) -> None:
        error_message: ErrorMessage | None = robot_pause_mission(
            self.signal_exit, self.robot, self.logger
        )

        if error_message:
            self.robot_service_events.mission_failed_to_pause.trigger_event(
                error_message
            )
        else:
            self.robot_service_events.mission_successfully_paused.trigger_event(
                EmptyMessage()
            )

    def _resume_mission_handler(self) -> None:
        error_message: ErrorMessage | None = robot_resume_mission(
            self.signal_exit, self.robot, self.logger
        )

        if error_message:
            self.robot_service_events.mission_failed_to_resume.trigger_event(
                error_message
            )
        else:
            self.robot_service_events.mission_successfully_resumed.trigger_event(
                EmptyMessage()
            )

    def _upload_inspection_event_handler(
        self, inspection: InspectionTask, mission: Mission
    ) -> None:
        robot_upload_inspection(
            self.robot, self.logger, inspection, mission, self.upload_queue
        )

    def _prune_upload_thread_list(self) -> None:
        if len(self.upload_inspection_threads) > 0:
            self.upload_inspection_threads[:] = [
                thread
                for thread in self.upload_inspection_threads
                if not thread.is_alive()
            ]

    def register_and_monitor_inspection_callback(
        self,
        callback_function: Callable,
    ) -> None:
        self.inspection_callback_function = callback_function

        self.inspection_callback_thread = self.robot.register_inspection_callback(
            callback_function
        )
        if self.inspection_callback_thread is not None:
            self.inspection_callback_thread.start()
            self.logger.info("Inspection callback thread started and will be monitored")

    def _restart_inspection_thread_if_stopped(self) -> None:
        if (
            self.inspection_callback_thread is not None
            and not self.inspection_callback_thread.is_alive()
        ):
            self.logger.warning("Inspection callback thread died - restarting")
            self.inspection_callback_thread.join()
            self.inspection_callback_thread.start()

    def _monitor_mission_done_handler(self) -> None:
        if (
            self.monitor_mission_thread is not None
            and not self.monitor_mission_thread.is_alive()
        ):
            mission_manually_cancelled = (
                self.monitor_mission_thread.signal_mission_stopped.is_set()
            )
            error_message = self.monitor_mission_thread.error_message
            if not mission_manually_cancelled:
                if error_message is not None:
                    self.robot_service_events.mission_failed.trigger_event(
                        error_message
                    )
                else:
                    self.robot_service_events.mission_succeeded.trigger_event(
                        EmptyMessage()
                    )
            self.monitor_mission_thread.join()
            self.monitor_mission_thread = None

    def _register_status_threads(self) -> None:
        self.status_thread = RobotStatusThread(
            robot=self.robot,
            signal_exit=self.signal_exit,
            shared_state=self.shared_state,
            state_machine_events=self.state_machine_events,
            robot_service_events=self.robot_service_events,
        )
        self.status_thread.start()

        self.battery_thread = RobotBatteryThread(
            self.robot, self.signal_exit, self.shared_state
        )
        self.battery_thread.start()

    def _process_state_machine_requests(self) -> FunctionThread | None:
        start_mission_request = self.state_machine_events.start_mission.consume_event()
        if start_mission_request:
            return FunctionThread(self._start_mission_handler, start_mission_request)

        pause_mission_request = self.state_machine_events.pause_mission.consume_event()
        if pause_mission_request:
            return FunctionThread(self._pause_mission_handler)

        resume_mission_request = (
            self.state_machine_events.resume_mission.consume_event()
        )
        if resume_mission_request:
            return FunctionThread(self._resume_mission_handler)

        stop_mission_request = self.state_machine_events.stop_mission.consume_event()
        if stop_mission_request:
            return FunctionThread(self._stop_mission_handler)

        return None

    def run(self) -> None:

        self._register_status_threads()

        try:
            while not self.signal_exit.wait(0):
                if self.action_thread is None or not self.action_thread.is_alive():
                    self.action_thread = self._process_state_machine_requests()
                    self._monitor_mission_done_handler()

                started_mission = (
                    self.robot_service_events.mission_started.consume_event()
                )
                if started_mission is not None:
                    self.monitor_mission_thread = RobotMonitorMissionThread(
                        lambda task: self.robot_service_events.request_inspection_upload.trigger_event(
                            (task, started_mission)
                        ),
                        self.robot,
                        self.mqtt_publisher,
                        self.signal_exit,
                        self.signal_mission_stopped,
                        started_mission,
                    )
                    self.monitor_mission_thread.start()

                upload_request: Tuple[(InspectionTask, Mission)] | None = (
                    self.robot_service_events.request_inspection_upload.consume_event()
                )
                if upload_request is not None:
                    self.upload_inspection_threads.append(
                        FunctionThread(
                            self._upload_inspection_event_handler,
                            upload_request[0],
                            upload_request[1],
                        )
                    )

                self._prune_upload_thread_list()

                if settings.UPLOAD_INSPECTIONS_ASYNC:
                    self._restart_inspection_thread_if_stopped()
        except Exception as e:
            self.logger.error(f"Unhandled exception in robot service: {str(e)}")
        self.logger.info("Exiting robot service main thread")
