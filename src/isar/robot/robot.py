import logging
from threading import Event
from typing import Optional

from injector import inject

from isar.models.communication.queues.queue_io import QueueIO
from isar.models.communication.queues.queue_utils import check_for_event
from isar.models.communication.queues.queues import Queues
from isar.robot.robot_start_mission import RobotStartMissionThread
from isar.robot.robot_status import RobotStatusThread
from isar.robot.robot_task_status import RobotTaskStatusThread
from robot_interface.robot_interface import RobotInterface


class Robot(object):

    @inject
    def __init__(self, queues: Queues, robot: RobotInterface):
        self.logger = logging.getLogger("robot")
        self.queues: Queues = queues
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

    def _check_and_handle_start_mission(self, queue: QueueIO) -> None:
        start_mission = check_for_event(queue)
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
                self.queues,
                self.robot,
                self.signal_thread_quitting,
                start_mission,
            )
            self.start_mission_thread.start()

    def _check_and_handle_task_status_request(self, queue: QueueIO) -> None:
        task_id = check_for_event(queue)
        if task_id:
            self.robot_task_status_thread = RobotTaskStatusThread(
                self.queues, self.robot, self.signal_thread_quitting, task_id
            )
            self.robot_task_status_thread.start()

    def run(self) -> None:
        self.robot_status_thread = RobotStatusThread(
            self.queues, self.robot, self.signal_thread_quitting
        )
        self.robot_status_thread.start()

        while True:
            if self.signal_thread_quitting.is_set():
                break

            self._check_and_handle_start_mission(
                self.queues.state_machine_start_mission
            )

            self._check_and_handle_task_status_request(
                self.queues.state_machine_task_status_request
            )

        self.logger.info("Exiting robot service main thread")
