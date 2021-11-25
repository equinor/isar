from dataclasses import dataclass
from typing import Optional

from isar.config import config


@dataclass
class RecommendedMetadata:
    date: Optional[str] = None
    sensor_carrier_id: str = config.get("metadata", "robot_id")
    sensor_carrier_type: str = config.get("metadata", "robot_type")
    plant_code: str = config.get("metadata", "plant_code")
    plant_name: str = config.get("metadata", "plant_name")
    country: str = config.get("metadata", "country")
    contractor: str = config.get("metadata", "contractor")
    mission_type: str = config.get("metadata", "mission_type")
