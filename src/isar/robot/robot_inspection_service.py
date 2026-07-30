import logging
from threading import Event as ThreadEvent
from threading import Thread
from typing import Callable, List, Tuple

from isar.config.settings import settings
from isar.models.events import Event, Events
from isar.robot.function_thread import FunctionThread
from isar.storage.uploader import Uploader
from robot_interface.models.exceptions.robot_exceptions import (
    RobotException,
    RobotRetrieveInspectionException,
)
from robot_interface.models.inspection.inspection import Inspection
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import InspectionTask
from robot_interface.robot_interface import RobotInterface


def fetch_and_upload_inspection(
    get_inspection_function: Callable[[InspectionTask], Inspection],
    logger: logging.Logger,
    task: InspectionTask,
    mission: Mission,
    upload_inspection_event: Event[Tuple[Inspection, Mission]],
) -> None:
    try:
        inspection: Inspection = get_inspection_function(task)
        if task.id != inspection.id:
            logger.warning(
                f"The id of task ({task.id}) "
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
    inspection.metadata.analysis_types = task.analysis_types

    message: Tuple[Inspection, Mission] = (
        inspection,
        mission,
    )
    upload_inspection_event.trigger_event(message)
    logger.info(f"Inspection result: {str(inspection.id)[:8]} queued for upload")


class RobotInspectionService:
    def __init__(
        self,
        events: Events,
        robot: RobotInterface,
        uploader: Uploader,
    ) -> None:
        self.logger = logging.getLogger("uploader")
        self.upload_task_event: Event[Tuple[InspectionTask, Mission]] = (
            events.robot_service_events.request_inspection_upload
        )
        self.upload_inspection_event: Event[Tuple[Inspection, Mission]] = (
            events.upload_queue
        )
        self.uploader: Uploader = uploader
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
        callback_function: Callable[[Inspection, Mission], None],
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

                upload_task_request: Tuple[(InspectionTask, Mission)] | None = (
                    self.upload_task_event.consume_event()
                )

                if upload_task_request is not None:
                    self.upload_inspection_threads.append(
                        FunctionThread(
                            fetch_and_upload_inspection,
                            self.robot.get_inspection,
                            self.logger,
                            upload_task_request[0],
                            upload_task_request[1],
                            self.upload_inspection_event,
                        )
                    )

                upload_inspection_request: Tuple[Inspection, Mission] | None = (
                    self.upload_inspection_event.consume_event()
                )

                if upload_inspection_request is not None:
                    self.upload_inspection_threads.append(
                        FunctionThread(
                            self.uploader.upload_inspection,
                            upload_inspection_request[0],
                            upload_inspection_request[1],
                        )
                    )

                self._prune_upload_thread_list()

                if settings.UPLOAD_INSPECTIONS_ASYNC:
                    self._restart_inspection_thread_if_stopped()
        except Exception as e:
            self.logger.error(f"Unhandled exception in robot service: {str(e)}")
        self.logger.info("Exiting robot service main thread")
