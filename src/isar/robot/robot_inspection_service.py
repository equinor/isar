import logging
from queue import Queue
from threading import Event as ThreadEvent
from threading import Thread
from typing import Callable, List, Tuple

from isar.config.settings import settings
from isar.models.events import Events, RobotServiceEvents, StateMachineEvents
from isar.robot.function_thread import FunctionThread
from robot_interface.models.exceptions.robot_exceptions import (
    RobotException,
    RobotRetrieveInspectionException,
)
from robot_interface.models.inspection.inspection import Inspection
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import InspectionTask
from robot_interface.robot_interface import RobotInterface
from robot_interface.telemetry.mqtt_client import MqttClientInterface


def robot_upload_inspection(
    robot: RobotInterface,
    logger: logging.Logger,
    task: InspectionTask,
    mission: Mission,
    upload_queue: Queue,
) -> None:
    try:
        inspection: Inspection = robot.get_inspection(task=task)
        if task.inspection_id != inspection.id:
            logger.warning(
                f"The inspection_id of task ({task.inspection_id}) "
                f"and result ({inspection.id}) is not matching. "
                f"This may lead to confusions when accessing the inspection later"
            )

    except (RobotRetrieveInspectionException, RobotException) as e:
        logger.error(f"Failed to retrieve inspections because: {e.error_description}")
        return
    except Exception as e:
        logger.error(f"Failed to retrieve inspections because of unexpected error: {e}")
        return

    if not inspection:
        logger.warning(
            f"No inspection result data retrieved for task {str(task.id)[:8]}"
        )

    inspection.metadata.tag_id = task.tag_id

    message: Tuple[Inspection, Mission] = (
        inspection,
        mission,
    )
    upload_queue.put(message)
    logger.info(f"Inspection result: {str(inspection.id)[:8]} queued for upload")


class RobotInspectionService:
    def __init__(
        self,
        events: Events,
        robot: RobotInterface,
        mqtt_publisher: MqttClientInterface,
    ) -> None:
        self.logger = logging.getLogger("uploader")
        self.state_machine_events: StateMachineEvents = events.state_machine_events
        self.robot_service_events: RobotServiceEvents = events.robot_service_events
        self.mqtt_publisher: MqttClientInterface = mqtt_publisher
        self.upload_queue: Queue = events.upload_queue
        self.robot: RobotInterface = robot
        self.upload_inspection_threads: List[FunctionThread] = []
        self.signal_exit: ThreadEvent = ThreadEvent()
        self.inspection_callback_thread: Thread | None = None

    def stop(self) -> None:
        self.signal_exit.set()
        for thread in self.upload_inspection_threads:
            if thread.is_alive():
                thread.join()
        self.upload_inspection_threads = []
        self.action_thread = None

    def _prune_upload_thread_list(self) -> None:
        if len(self.upload_inspection_threads) > 0:
            self.upload_inspection_threads[:] = [
                thread
                for thread in self.upload_inspection_threads
                if not thread.is_alive()
            ]

    def _restart_inspection_thread_if_stopped(self) -> None:
        if (
            self.inspection_callback_thread is not None
            and not self.inspection_callback_thread.is_alive()
        ):
            self.logger.warning("Inspection callback thread died - restarting")
            self.inspection_callback_thread.join()
            self.inspection_callback_thread.start()

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

    def run(self) -> None:
        try:
            while not self.signal_exit.wait(0):
                upload_request: Tuple[(InspectionTask, Mission)] | None = (
                    self.robot_service_events.request_inspection_upload.consume_event()
                )
                if upload_request is not None:
                    self.upload_inspection_threads.append(
                        FunctionThread(
                            robot_upload_inspection,
                            self.robot,
                            self.logger,
                            upload_request[0],
                            upload_request[1],
                            self.upload_queue,
                        )
                    )

                self._prune_upload_thread_list()

                if settings.UPLOAD_INSPECTIONS_ASYNC:
                    self._restart_inspection_thread_if_stopped()
        except Exception as e:
            self.logger.error(f"Unhandled exception in robot service: {str(e)}")
        self.logger.info("Exiting robot service main thread")
