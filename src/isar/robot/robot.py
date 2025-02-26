import logging
from queue import Queue
from threading import Event
from typing import Optional

from injector import inject

from isar.models.communication.queues.queue_utils import check_for_event
from isar.models.communication.queues.queues import Events, SharedState
from isar.robot.robot_start_mission import RobotStartMissionThread
from isar.robot.robot_status import RobotStatusThread
from isar.robot.robot_task_status import RobotTaskStatusThread
from robot_interface.robot_interface import RobotInterface


class Robot(object):

    @inject
    def __init__(
        self, events: Events, robot: RobotInterface, shared_state: SharedState
    ):
        self.logger = logging.getLogger("robot")
        self.events: Events = events
        self.shared_state: SharedState = shared_state
        self.robot: RobotInterface = robot
        self.start_mission_thread: Optional[RobotStartMissionThread] = None
        self.robot_status_thread: Optional[RobotStatusThread] = None
        self.robot_task_status_thread: Optional[RobotTaskStatusThread] = None
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
                self.events,
                self.robot,
                self.signal_thread_quitting,
                start_mission,
            )
            self.start_mission_thread.start()

    def _check_and_handle_task_status_request(self, event: Queue) -> None:
        task_id = check_for_event(event)
        if task_id:
            self.robot_task_status_thread = RobotTaskStatusThread(
                self.events, self.robot, self.signal_thread_quitting, task_id
            )
            self.robot_task_status_thread.start()

    def run(self) -> None:
        self.robot_status_thread = RobotStatusThread(
            self.robot, self.signal_thread_quitting, self.shared_state
        )
        self.robot_status_thread.start()

        while True:
            if self.signal_thread_quitting.is_set():
                break

            self._check_and_handle_start_mission(
                self.events.state_machine_events.state_machine_start_mission
            )

            self._check_and_handle_task_status_request(
                self.events.state_machine_events.state_machine_task_status_request
            )

        self.logger.info("Exiting robot service main thread")
