from dataclasses import dataclass
from typing import Optional

from isar.config import config


@dataclass
class RecommendedMetadata:
    date: Optional[str] = None
    sensor_carrier_id: str = config.get("metadata", "eqrobot_robot_id")
    sensor_carrier_type: str = config.get("metadata", "eqrobot_robot_type")
    plant_code: str = config.get("metadata", "eqrobot_plant_code")
    plant_name: str = config.get("metadata", "eqrobot_plant_name")
    country: str = config.get("metadata", "country")
    contractor: str = config.get("metadata", "contractor")
    mission_type: str = config.get("metadata", "mission_type")
