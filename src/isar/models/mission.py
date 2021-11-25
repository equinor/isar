from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Union
from uuid import UUID

from isar.config import config
from isar.models.mission_metadata.mission_metadata import MissionMetadata
from robot_interface.models.step import Step


@dataclass
class Mission:
    mission_steps: List[Step]
    mission_id: Union[UUID, int, str, None] = None
    mission_metadata: MissionMetadata = None

    def __post_init__(self) -> None:
        if self.mission_id is None:
            plant_short_name: str = config.get("metadata", "plant_short_name")
            robot_id: str = config.get("metadata", "eqrobot_robot_id")
            now: datetime = datetime.utcnow()

            self.mission_id = f"{plant_short_name.upper()}{robot_id.upper()}{now.strftime('%d%m%Y%H%M')}"

        if self.mission_metadata is None:
            self.mission_metadata = MissionMetadata(mission_id=self.mission_id)
