import logging
from queue import Queue
from typing import Tuple

from robot_interface.models.exceptions.robot_exceptions import (
    RobotException,
    RobotRetrieveInspectionException,
)
from robot_interface.models.inspection.inspection import Inspection
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import InspectionTask
from robot_interface.robot_interface import RobotInterface


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
