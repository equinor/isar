from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Union
from uuid import UUID

from isar.config import config
from isar.models.mission_metadata.mission_metadata import MissionMetadata
from robot_interface.models.inspection.inspection import Inspection
from robot_interface.models.mission import STEPS


@dataclass
class Mission:
    mission_steps: List[STEPS]
    mission_id: Union[UUID, int, str, None] = None
    inspections: List[Inspection] = field(default_factory=list)
    mission_metadata: MissionMetadata = None

    def set_unique_mission_id_and_metadata(self) -> None:
        self._set_unique_mission_id()
        self.mission_metadata = MissionMetadata(mission_id=self.mission_id)

    def _set_unique_mission_id(self) -> None:
        plant_short_name: str = config.get("metadata", "plant_short_name")
        robot_id: str = config.get("metadata", "robot_id")
        now: datetime = datetime.utcnow()
        self.mission_id = (
            f"{plant_short_name.upper()}{robot_id.upper()}{now.strftime('%d%m%Y%H%M')}"
        )

    def __post_init__(self) -> None:
        if self.mission_id is None:
            self._set_unique_mission_id()

        if self.mission_metadata is None:
            self.mission_metadata = MissionMetadata(mission_id=self.mission_id)
