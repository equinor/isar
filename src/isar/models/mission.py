from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Union
from uuid import UUID

from isar.config import config
from isar.models.mission_metadata.mission_metadata import MissionMetadata
from robot_interface.models.inspection.inspection import Inspection
from robot_interface.models.mission import TASKS


@dataclass
class Mission:
    tasks: List[TASKS]
    id: Union[UUID, int, str, None] = None
    inspections: List[Inspection] = field(default_factory=list)
    metadata: MissionMetadata = None

    def set_unique_id_and_metadata(self) -> None:
        self._set_unique_id()
        self.metadata = MissionMetadata(mission_id=self.id)

    def _set_unique_id(self) -> None:
        plant_short_name: str = config.get("metadata", "plant_short_name")
        robot_id: str = config.get("metadata", "robot_id")
        now: datetime = datetime.utcnow()
        self.id = (
            f"{plant_short_name.upper()}{robot_id.upper()}{now.strftime('%d%m%Y%H%M')}"
        )

    def __post_init__(self) -> None:
        if self.id is None:
            self._set_unique_id()

        if self.metadata is None:
            self.metadata = MissionMetadata(mission_id=self.id)
