from dataclasses import dataclass
from typing import Optional

from isar.config import config


@dataclass
class RequiredMetadata:
    mission_id: Optional[str] = None
    data_scheme: str = config.get("metadata", "data_scheme")
    time_zone: str = config.get("metadata", "timezone")
    coordinate_reference_system: str = config.get(
        "metadata", "coordinate_reference_system"
    )
    vertical_reference_system: str = config.get("metadata", "vertical_reference_system")
    sensor_carrier_orientation_reference_system: str = config.get(
        "metadata", "sensor_carrier_orientation_reference_system"
    )
    url: Optional[str] = None
    data_classification: str = config.get("metadata", "data_classification")
