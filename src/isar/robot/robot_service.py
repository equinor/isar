import asyncio
import logging
from threading import Event as ThreadEvent
from uuid import uuid4

from isar.models.events import (
    AbortedMission,
    EmptyMessage,
    Event,
    Events,
    RobotActionRequests,
    RobotAsyncEvents,
)
from isar.models.mqtt_queue import MQTTQueue
from isar.robot.robot_battery import RobotBatteryThread
from isar.robot.robot_monitor_mission import (
    robot_monitor_mission,
    robot_monitor_return_home_mission,
)
from isar.robot.robot_pause_mission import robot_pause_mission
from isar.robot.robot_resume_mission import robot_resume_mission
from isar.robot.robot_return_home import robot_return_home
from isar.robot.robot_start_mission import robot_start_mission
from isar.robot.robot_status import RobotStatusThread
from isar.robot.robot_stop_mission import robot_stop_mission
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus
from robot_interface.models.mission.task import InspectionTask
from robot_interface.robot_interface import RobotInterface


class RobotService:
    def __init__(
        self,
        events: Events,
        robot: RobotInterface,
        mqtt_queue: MQTTQueue,
    ) -> None:
        self.logger = logging.getLogger("robot")
        self.action_requests: RobotActionRequests = events.action_requests
        self.robot_async_events: RobotAsyncEvents = events.robot_async_events
        self.mqtt_queue: MQTTQueue = mqtt_queue
        self.upload_task_event: Event[tuple[InspectionTask, Mission]] = (
            events.upload_task_event
        )
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

    def _start_return_home_handler(self, mission_id: str) -> bool:
        error_message: ErrorMessage | None = robot_return_home(
            self.signal_exit, self.robot, self.logger, mission_id
        )

        if (
            error_message
            and error_message.error_reason == ErrorReason.RobotAlreadyHomeException
        ):
            self.logger.info("Did not start return home, since robot was already home")
            self.action_requests.return_home.trigger_success_response(EmptyMessage())
            return False
        elif error_message:
            error_message.error_description = (
                f"Failed to initiate due to: {error_message.error_description}"
            )
            self.logger.warning(f"Failed to return home mission. {error_message}")
            self.action_requests.return_home.trigger_failure_response(error_message)
            return False
        self.logger.info("Received confirmation that return home mission has started")
        return True

    def _start_mission_handler(self, mission: Mission) -> bool:
        error_message: ErrorMessage | None = robot_start_mission(
            self.signal_exit, self.robot, self.logger, mission
        )

        if error_message:
            error_message.error_description = (
                f"Failed to initiate due to: {error_message.error_description}"
            )
            self.logger.warning(f"Failed to start mission. {error_message}")
            self.action_requests.execute_mission.trigger_failure_response(error_message)
            return False
        self.logger.info("Received confirmation that mission has started")
        return True

    async def _stop_mission_handler(
        self,
        monitor_mission_task: asyncio.Task[AbortedMission | None] | None,
        mission: Mission | None = None,
    ) -> None:
        error_message: ErrorMessage | None = robot_stop_mission(
            self.signal_exit, self.robot, self.logger
        )

        if error_message:
            self.logger.warning(f"Failed to stop mission. {error_message}")
            self.action_requests.stop_mission.trigger_failure_response(EmptyMessage())
            return

        if monitor_mission_task is not None:
            if not monitor_mission_task.done():
                monitor_mission_task.cancel()
            aborted_mission: AbortedMission | None = None
            try:
                aborted_mission = await monitor_mission_task
            except asyncio.CancelledError:
                # The monitor may be cancelled before its coroutine starts.
                if mission is not None and mission.robot_mission_id is not None:
                    aborted_mission = mission

            if aborted_mission is not None:
                if (
                    aborted_mission.robot_mission_id is not None
                    and aborted_mission.status
                    in [
                        MissionStatus.NotStarted,
                        MissionStatus.InProgress,
                        MissionStatus.Paused,
                    ]
                ):
                    self.mqtt_queue.publish_mission_aborted(
                        aborted_mission.id,
                        "Stored mission stopped; automatic restart is not supported",
                    )
                unfinished_tasks = aborted_mission._get_unfinished_tasks()
                if len(unfinished_tasks) > 0:
                    continued_mission = Mission(
                        id=aborted_mission.id,
                        name=aborted_mission.name,
                        tasks=unfinished_tasks,
                    )
                    self.action_requests.stop_mission.trigger_success_response(
                        continued_mission
                    )
                    return

        self.action_requests.stop_mission.trigger_success_response(EmptyMessage())

    def _pause_mission_handler(self) -> None:
        error_message: ErrorMessage | None = robot_pause_mission(
            self.signal_exit, self.robot, self.logger
        )

        if error_message:
            self.logger.warning(f"Failed to pause mission. {error_message}")
            self.action_requests.pause_mission.trigger_failure_response(EmptyMessage())
        else:
            self.action_requests.pause_mission.trigger_success_response(EmptyMessage())

    def _resume_mission_handler(self) -> None:
        error_message: ErrorMessage | None = robot_resume_mission(
            self.signal_exit, self.robot, self.logger
        )

        if error_message:
            self.logger.warning(f"Failed to resume mission. {error_message}")
            self.action_requests.resume_mission.trigger_failure_response(EmptyMessage())
        else:
            self.action_requests.resume_mission.trigger_success_response(EmptyMessage())

    async def _monitor_return_home_handler(self, mission_id: str) -> None:
        error_message: ErrorMessage | None = None
        is_aborted: bool = True
        try:
            error_message, is_aborted = await robot_monitor_return_home_mission(
                mission_id, self.robot
            )

            if is_aborted:
                return

            if error_message is not None:
                self.logger.warning(
                    f"Error monitoring return home mission. {error_message}"
                )
                self.action_requests.return_home.trigger_failure_response(error_message)
            else:
                self.action_requests.return_home.trigger_success_response(
                    EmptyMessage()
                )
        except asyncio.CancelledError:
            pass

    async def _monitor_mission_handler(self, mission: Mission) -> AbortedMission | None:
        remaining_mission: Mission | None = None
        try:
            error_message, remaining_mission, is_aborted = await robot_monitor_mission(
                mission,
                self.robot,
                lambda task: self.upload_task_event.trigger_event((task, mission)),
                self.mqtt_queue,
            )
            if is_aborted:
                return remaining_mission

            if error_message is not None:
                self.logger.warning(f"Error monitoring mission. {error_message}")
                self.action_requests.execute_mission.trigger_failure_response(
                    error_message
                )
            else:
                self.action_requests.execute_mission.trigger_success_response(
                    mission.status
                    if mission.robot_mission_id is not None
                    else EmptyMessage()
                )
        except asyncio.CancelledError:
            pass
        return mission if remaining_mission is None else remaining_mission

    def _register_status_threads(self) -> None:
        self.status_thread = RobotStatusThread(
            robot=self.robot,
            signal_exit=self.signal_exit,
            robot_async_events=self.robot_async_events,
        )
        self.status_thread.start()

        self.battery_thread = RobotBatteryThread(
            self.robot,
            self.signal_exit,
            self.robot_async_events.battery_below_mission_threshold,
            self.robot_async_events.battery_above_recharge_threshold,
        )
        self.battery_thread.start()

    async def _run_main_event_loop(self) -> None:
        monitor_mission_task: asyncio.Task[AbortedMission | None] | None = None
        monitored_mission: Mission | None = None

        while not self.signal_exit.is_set():

            return_home_request = (
                self.action_requests.return_home.request.consume_event()
            )
            if return_home_request:
                return_home_mission_id = str(uuid4())
                success = self._start_return_home_handler(return_home_mission_id)
                if success:
                    monitored_mission = None
                    monitor_mission_task = asyncio.create_task(
                        self._monitor_return_home_handler(return_home_mission_id)
                    )

            start_mission_request = (
                self.action_requests.execute_mission.request.consume_event()
            )
            if start_mission_request:
                success = self._start_mission_handler(start_mission_request)
                if success:
                    monitored_mission = start_mission_request
                    monitor_mission_task = asyncio.create_task(
                        self._monitor_mission_handler(start_mission_request)
                    )

            pause_mission_request = (
                self.action_requests.pause_mission.request.consume_event()
            )
            if pause_mission_request:
                self._pause_mission_handler()

            resume_mission_request = (
                self.action_requests.resume_mission.request.consume_event()
            )
            if resume_mission_request:
                self._resume_mission_handler()

            stop_mission_request = (
                self.action_requests.stop_mission.request.consume_event()
            )
            if stop_mission_request:
                await self._stop_mission_handler(
                    monitor_mission_task, monitored_mission
                )
                monitor_mission_task = None
                monitored_mission = None

            if monitor_mission_task is not None and monitor_mission_task.done():
                try:
                    await monitor_mission_task
                except asyncio.CancelledError:  # This is not expected
                    self.logger.warning(
                        "Mission monitor task was cancelled outside stop mission handler"
                    )
                monitor_mission_task = None
                monitored_mission = None

            await asyncio.sleep(0.01)

    def run(self) -> None:

        self._register_status_threads()
        asyncio.run(self._run_main_event_loop())
