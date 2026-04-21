import asyncio
import logging
from threading import Event as ThreadEvent

from isar.models.events import (
    AbortedMission,
    EmptyMessage,
    Events,
    RobotServiceEvents,
    SharedState,
    StateMachineEvents,
)
from isar.robot.robot_battery import RobotBatteryThread
from isar.robot.robot_monitor_mission import robot_monitor_mission
from isar.robot.robot_pause_mission import robot_pause_mission
from isar.robot.robot_resume_mission import robot_resume_mission
from isar.robot.robot_start_mission import robot_start_mission
from isar.robot.robot_status import RobotStatusThread
from isar.robot.robot_stop_mission import robot_stop_mission
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
        self.shared_state: SharedState = shared_state
        self.robot: RobotInterface = robot
        self.battery_thread: RobotBatteryThread | None = None
        self.status_thread: RobotStatusThread | None = None
        self.signal_exit: ThreadEvent = ThreadEvent()

    def stop(self) -> None:
        self.signal_exit.set()
        if self.status_thread is not None and self.status_thread.is_alive():
            self.status_thread.join()
        if self.battery_thread is not None and self.battery_thread.is_alive():
            self.battery_thread.join()
        self.status_thread = None
        self.battery_thread = None

    def _start_mission_handler(self, mission: Mission) -> bool:
        error_message: ErrorMessage | None = robot_start_mission(
            self.signal_exit, self.robot, self.logger, mission
        )

        if (
            error_message
            and error_message.error_reason == ErrorReason.RobotAlreadyHomeException
        ):
            self.robot_service_events.robot_already_home.trigger_event(EmptyMessage())
            return False
        elif error_message:
            mission.status = MissionStatus.Failed
            error_message.error_description = (
                f"Failed to initiate due to: {error_message.error_description}"
            )
            self.robot_service_events.mission_failed.trigger_event(error_message)
            return False
        if not mission._is_return_to_home_mission():
            self.robot_service_events.mission_started_successfully.trigger_event(
                EmptyMessage()
            )
        self.logger.info("Received confirmation that mission has started")
        return True

    async def _stop_mission_handler(
        self, monitor_mission_task: asyncio.Task[AbortedMission | None] | None
    ) -> None:
        error_message: ErrorMessage | None = robot_stop_mission(
            self.signal_exit, self.robot, self.logger
        )

        if error_message:
            self.robot_service_events.mission_failed_to_stop.trigger_event(
                error_message
            )
            return

        if monitor_mission_task is not None:
            if not monitor_mission_task.done():
                monitor_mission_task.cancel()
            aborted_mission: AbortedMission | None = None
            try:
                aborted_mission = await monitor_mission_task
            except asyncio.CancelledError:
                pass  # This happens if the monitor task is cancelled before it starts

            if aborted_mission is not None:
                unfinished_tasks = aborted_mission._get_unfinished_tasks()
                if len(unfinished_tasks) > 0:
                    continued_mission = Mission(
                        id=aborted_mission.id,
                        name=aborted_mission.name,
                        tasks=unfinished_tasks,
                        start_pose=aborted_mission.start_pose,
                    )
                    self.robot_service_events.mission_successfully_stopped.trigger_event(
                        continued_mission
                    )
                    return
        # This is here in case monitor is cancelled at the exact time it sets these events
        self.robot_service_events.mission_succeeded.clear_event()
        self.robot_service_events.mission_failed.clear_event()

        self.robot_service_events.stopped_mission_already_done.trigger_event(
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

    async def _monitor_mission_handler(self, mission: Mission) -> Mission | None:
        remaining_mission: Mission | None = None
        try:
            should_report_task_status = not mission._is_return_to_home_mission()

            def request_inspection_upload(task: InspectionTask) -> None:
                self.robot_service_events.request_inspection_upload.trigger_event(
                    (task, mission)
                )

            error_message, remaining_mission, is_aborted = await robot_monitor_mission(
                mission,
                self.robot,
                request_inspection_upload,
                self.mqtt_publisher,
                should_report_task_status,
            )
            if is_aborted:
                return remaining_mission

            if error_message is not None:
                self.robot_service_events.mission_failed.trigger_event(error_message)
            else:
                self.robot_service_events.mission_succeeded.trigger_event(
                    EmptyMessage()
                )
        except asyncio.CancelledError:
            pass
        finally:
            return mission if remaining_mission is None else remaining_mission

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

    async def _run_main_event_loop(self) -> None:
        monitor_mission_task: asyncio.Task[AbortedMission | None] | None = None

        try:
            while not self.signal_exit.wait(0):
                start_mission_request = (
                    self.state_machine_events.start_mission.consume_event()
                )
                if start_mission_request:
                    success = self._start_mission_handler(start_mission_request)
                    if success:
                        monitor_mission_task = asyncio.create_task(
                            self._monitor_mission_handler(start_mission_request)
                        )

                pause_mission_request = (
                    self.state_machine_events.pause_mission.consume_event()
                )
                if pause_mission_request:
                    self._pause_mission_handler()

                resume_mission_request = (
                    self.state_machine_events.resume_mission.consume_event()
                )
                if resume_mission_request:
                    self._resume_mission_handler()

                stop_mission_request = (
                    self.state_machine_events.stop_mission.consume_event()
                )
                if stop_mission_request:
                    await self._stop_mission_handler(monitor_mission_task)
                    monitor_mission_task = None

                if monitor_mission_task is not None and monitor_mission_task.done():
                    try:
                        await monitor_mission_task
                    except asyncio.CancelledError:  # This is not expected
                        self.logger.warning(
                            "Mission monitor task was cancelled outside stop mission handler"
                        )
                        pass
                    monitor_mission_task = None

                await asyncio.sleep(0)

        except Exception as e:
            self.logger.error(f"Unhandled exception in robot service: {str(e)}")
        self.logger.info("Exiting robot service main thread")

    def run(self) -> None:

        self._register_status_threads()
        asyncio.run(self._run_main_event_loop())
