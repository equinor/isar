import json
from pathlib import Path
from typing import Tuple

from isar.models.mission_metadata.mission_metadata import MissionMetadata
from robot_interface.models.inspection.inspection import Inspection
from robot_interface.utilities.json_service import EnhancedJSONEncoder


def construct_local_paths(
    inspection: Inspection, metadata: MissionMetadata
) -> Tuple[Path, Path]:
    folder: Path = Path(str(metadata.mission_id))
    filename: str = get_filename(
        mission_id=metadata.mission_id,
        inspection_type=type(inspection).__name__,
        inspection_id=inspection.id,
    )

    inspection_path: Path = folder.joinpath(
        f"{filename}.{inspection.metadata.file_type}"
    )

    metadata_path: Path = folder.joinpath(f"{filename}.json")

    return inspection_path, metadata_path


def construct_metadata_file(
    inspection: Inspection, metadata: MissionMetadata, filename: str
) -> bytes:
    data: dict = {
        "coordinate_reference_system": metadata.coordinate_reference_system,
        "vertical_reference_system": metadata.vertical_reference_system,
        "data_classification": metadata.data_classification,
        "source_url": None,
        "plant_code": metadata.plant_code,
        "media_orientation_reference_system": metadata.media_orientation_reference_system,  # noqa: E501
        "additional_meta": {
            "mission_id": metadata.mission_id,
            "plant_name": metadata.plant_name,
            "mission_date": metadata.mission_date,
            "isar_id": metadata.isar_id,
            "robot_name": metadata.robot_name,
        },
        "data": [
            {
                "folder": f"/{metadata.mission_id}",
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
    mission_id: str,
    inspection_type: str,
    inspection_id: str,
) -> str:
    return f"{mission_id}_{inspection_type}_{inspection_id}"
