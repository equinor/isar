from dataclasses import dataclass
from datetime import datetime
from typing import List, Union
from uuid import UUID

from isar.config.settings import settings
from isar.models.mission_metadata.mission_metadata import MissionMetadata
from robot_interface.models.mission import STEPS
from robot_interface.models.mission.step import DriveToPose, InspectionStep


@dataclass
class Mission:
    steps: List[STEPS]
    id: Union[UUID, int, str, None] = None
    metadata: MissionMetadata = None

    def set_unique_id_and_metadata(self) -> None:
        self._set_unique_id()
        self.metadata = MissionMetadata(mission_id=self.id)

    def set_step_dependencies(self):
        last_drive_to_step = None
        for step in self.steps:
            if isinstance(step, DriveToPose):
                last_drive_to_step = step
                if step.depends_on:
                    step.depends_on = [self.steps[ind].id for ind in step.depends_on]
            elif isinstance(step, InspectionStep):
                if step.depends_on is None:
                    step.depends_on = [last_drive_to_step.id]
                else:
                    step.depends_on = [self.steps[ind].id for ind in step.depends_on]

    def _set_unique_id(self) -> None:
        plant_short_name: str = settings.PLANT_SHORT_NAME
        robot_id: str = settings.ROBOT_ID
        now: datetime = datetime.utcnow()
        self.id = (
            f"{plant_short_name.upper()}{robot_id.upper()} "
            f"{now.strftime('%d%m%Y%H%M%S%f')[:-3]}"
        )

    def __post_init__(self) -> None:
        if self.id is None:
            self._set_unique_id()

        if self.metadata is None:
            self.metadata = MissionMetadata(mission_id=self.id)
