from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from isar.config.settings import settings

additional_meta: dict = {}


@dataclass
class MissionMetadata:
    mission_id: str
    coordinate_reference_system: str = settings.COORDINATE_REFERENCE_SYSTEM
    vertical_reference_system: str = settings.VERTICAL_REFERENCE_SYSTEM
    data_classification: str = settings.DATA_CLASSIFICATION
    source_url: Optional[str] = None
    plant_code: str = settings.PLANT_CODE
    plant_name: str = settings.PLANT_NAME
    plant_short_name: str = settings.PLANT_SHORT_NAME
    media_orientation_reference_system: str = (
        settings.MEDIA_ORIENTATION_REFERENCE_SYSTEM
    )
    isar_id: str = settings.ISAR_ID
    robot_name: str = settings.ROBOT_NAME
    robot_model: str = settings.ROBOT_TYPE
    mission_date: date = datetime.utcnow().date()
