from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Union
from uuid import UUID

from isar.config import config

additional_meta: dict = {}


@dataclass
class MissionMetadata:
    mission_id: Union[UUID, int, str, None]
    coordinate_reference_system: str = config.get(
        "metadata", "coordinate_reference_system"
    )
    vertical_reference_system: str = config.get("metadata", "vertical_reference_system")
    data_classification: str = config.get("metadata", "data_classification")
    source_url: Optional[str] = None
    plant_code: str = config.get("metadata", "plant_code")
    plant_name: str = config.get("metadata", "plant_name")
    media_orientation_reference_system: str = config.get(
        "metadata", "media_orientation_reference_system"
    )
    robot_id: str = config.get("metadata", "robot_type")
    mission_date: date = datetime.utcnow().date()
