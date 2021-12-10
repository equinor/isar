from dataclasses import dataclass
from datetime import datetime
from typing import List, Union
from uuid import UUID

from isar.config import config
from isar.models.mission_metadata.mission_metadata import MissionMetadata
from robot_interface.models.mission import TASKS
from robot_interface.models.mission.task import DriveToPose, InspectionTask


@dataclass
class Mission:
    tasks: List[TASKS]
    id: Union[UUID, int, str, None] = None
    metadata: MissionMetadata = None

    def set_unique_id_and_metadata(self) -> None:
        self._set_unique_id()
        self.metadata = MissionMetadata(mission_id=self.id)

    def set_task_dependencies(self):
        last_drive_to_task = None
        for task_index, task in enumerate(self.tasks):
            if isinstance(task, DriveToPose):
                last_drive_to_task = task_index
            elif isinstance(task, InspectionTask):
                if task.depends_on is None:
                    task.depends_on = [last_drive_to_task]

    def _set_unique_id(self) -> None:
        plant_short_name: str = config.get("metadata", "plant_short_name")
        robot_id: str = config.get("metadata", "robot_id")
        now: datetime = datetime.utcnow()
        self.id = f"{plant_short_name.upper()}{robot_id.upper()}{now.strftime('%d%m%Y%H%M%S%f')[:-3]}"

    def __post_init__(self) -> None:
        if self.id is None:
            self._set_unique_id()

        if self.metadata is None:
            self.metadata = MissionMetadata(mission_id=self.id)
