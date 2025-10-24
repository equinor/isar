import logging
from queue import Queue
from threading import Thread
from typing import Tuple

from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    RobotException,
    RobotRetrieveInspectionException,
)
from robot_interface.models.inspection.inspection import Inspection
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import TASKS
from robot_interface.robot_interface import RobotInterface


class RobotUploadInspectionThread(Thread):
    def __init__(
        self,
        upload_queue: Queue,
        robot: RobotInterface,
        task: TASKS,
        mission: Mission,
    ):
        self.logger = logging.getLogger("robot")
        self.robot: RobotInterface = robot
        self.task: TASKS = task
        self.upload_queue = upload_queue
        self.mission: Mission = mission
        Thread.__init__(self, name=f"Robot inspection upload thread - {task.id}")

    def stop(self) -> None:
        return

    def run(self):
        try:
            inspection: Inspection = self.robot.get_inspection(task=self.task)
            if self.task.inspection_id != inspection.id:
                self.logger.warning(
                    f"The inspection_id of task ({self.task.inspection_id}) "
                    f"and result ({inspection.id}) is not matching. "
                    f"This may lead to confusions when accessing the inspection later"
                )

        except (RobotRetrieveInspectionException, RobotException) as e:
            error_message: ErrorMessage = ErrorMessage(
                error_reason=e.error_reason, error_description=e.error_description
            )
            self.task.error_message = error_message
            self.logger.error(
                f"Failed to retrieve inspections because: {e.error_description}"
            )
            return

        except Exception as e:
            self.logger.error(
                f"Failed to retrieve inspections because of unexpected error: {e}"
            )
            return

        if not inspection:
            self.logger.warning(
                f"No inspection result data retrieved for task {str(self.task.id)[:8]}"
            )

        inspection.metadata.tag_id = self.task.tag_id

        message: Tuple[Inspection, Mission] = (
            inspection,
            self.mission,
        )
        self.upload_queue.put(message)
        self.logger.info(
            f"Inspection result: {str(inspection.id)[:8]} queued for upload"
        )
