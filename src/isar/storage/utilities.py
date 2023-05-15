import json
import time
from pathlib import Path
from typing import Tuple

from robot_interface.models.mission.mission import Mission
from robot_interface.models.inspection.inspection import Inspection
from robot_interface.utilities.json_service import EnhancedJSONEncoder

from isar.config.settings import settings
from datetime import date, datetime


def construct_paths(inspection: Inspection, mission: Mission) -> Tuple[Path, Path]:
    folder: Path = Path(get_foldername(mission=mission))
    filename: str = get_filename(inspection=inspection)

    inspection_path: Path = folder.joinpath(
        f"{filename}.{inspection.metadata.file_type}"
    )

    metadata_path: Path = folder.joinpath(f"{filename}.json")

    return inspection_path, metadata_path


def construct_metadata_file(
    inspection: Inspection, mission: Mission, filename: str
) -> bytes:
    data: dict = {
        "coordinate_reference_system": settings.COORDINATE_REFERENCE_SYSTEM,
        "vertical_reference_system": settings.VERTICAL_REFERENCE_SYSTEM,
        "data_classification": settings.DATA_CLASSIFICATION,
        "source_url": None,
        "plant_code": settings.PLANT_CODE,
        "media_orientation_reference_system": settings.MEDIA_ORIENTATION_REFERENCE_SYSTEM,  # noqa: E501
        "additional_meta": {
            "mission_id": mission.id,
            "mission_name": mission.name,
            "plant_name": settings.PLANT_NAME,
            "mission_date": datetime.utcnow().date(),
            "isar_id": settings.ISAR_ID,
            "robot_name": settings.ROBOT_NAME,
        },
        "data": [
            {
                "folder": f"/{get_foldername(mission=mission)}",
                "files": [
                    {
                        "file_name": filename,
                        "timestamp": inspection.metadata.start_time,
                        "x": inspection.metadata.pose.position.x,
                        "y": inspection.metadata.pose.position.y,
                        "z": inspection.metadata.pose.position.z,
                        "tag": inspection.metadata.tag_id,
                        "additional_media_metadata": {
                            "orientation": inspection.metadata.pose.orientation.to_quat_array()  # noqa: E501
                        },
                    }
                ],
            }
        ],
    }

    return json.dumps(data, cls=EnhancedJSONEncoder, indent=4).encode()


def get_filename(
    inspection: Inspection,
) -> str:
    inspection_type: str = type(inspection).__name__
    tag: str = inspection.metadata.tag_id if inspection.metadata.tag_id else "no-tag"
    epoch_time: int = int(time.time())
    return f"{tag}__{inspection_type}__{epoch_time}"


def get_foldername(mission: Mission) -> str:
    return f"{datetime.utcnow().date()}__{settings.PLANT_SHORT_NAME}__{mission.name}__{mission.id}"
