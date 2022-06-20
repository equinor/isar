import json
from pathlib import Path
from typing import Any, Tuple
from uuid import UUID

from isar.models.mission_metadata.mission_metadata import MissionMetadata
from robot_interface.models.inspection.inspection import Image, Inspection, ThermalImage
from robot_interface.utilities.json_service import EnhancedJSONEncoder


def construct_local_paths(
    inspection: Inspection, metadata: MissionMetadata
) -> Tuple[Path, Path]:
    inspection_type: str = get_inspection_type(inspection=inspection)

    folder: Path = Path(str(metadata.mission_id))
    filename: str = get_filename(
        mission_id=metadata.mission_id,
        inspection_type=inspection_type,
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
            "robot_id": metadata.robot_id,
        },
        "data": [
            {
                "folder": f"/{metadata.mission_id}",
                "files": [
                    {
                        "file_name": filename,
                        "timestamp": inspection.metadata.start_time,
                        "x": inspection.metadata.time_indexed_pose.pose.position.x,
                        "y": inspection.metadata.time_indexed_pose.pose.position.y,
                        "z": inspection.metadata.time_indexed_pose.pose.position.z,
                        "tag": inspection.metadata.tag_id,
                        "additional_media_metadata": {
                            "orientation": inspection.metadata.time_indexed_pose.pose.orientation.to_quat_array()  # noqa: E501
                        },
                    }
                ],
            }
        ],
    }

    return json.dumps(data, cls=EnhancedJSONEncoder, indent=4).encode()


def get_filename(
    mission_id: Any,
    inspection_type: str,
    inspection_id: UUID,
) -> str:
    return f"{mission_id}_{inspection_type}_{inspection_id}"


def get_inspection_type(inspection: Inspection) -> str:
    if isinstance(inspection, Image):
        return "image"
    elif isinstance(inspection, ThermalImage):
        return "thermal"
    else:
        raise TypeError(
            f"Inspection must be either Image or ThermalImage. Got {type(inspection)}"
        )
