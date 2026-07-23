import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

from isar.config.settings import settings
from robot_interface.models.inspection.inspection import (
    AcousticMeasurementMetadata,
    Inspection,
)
from robot_interface.models.mission.mission import Mission


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
        "installation_code": settings.PLANT_SHORT_NAME,
        "additional_meta": {
            "inspection_id": inspection.id,
            "mission_id": mission.id,
            "mission_name": mission.name,
            "mission_date": datetime.now(timezone.utc)
            .date()
            .strftime("%Y-%m-%dT%H:%M:%S.%f"),
            "isar_id": settings.ISAR_ID,
            "robot_name": settings.ROBOT_NAME,
            "inspection_description": inspection.metadata.inspection_description,
            "tag": inspection.metadata.tag_id,
            "analysis_types": inspection.metadata.analysis_types,
            "robot_pose": {
                "position": {
                    "x": inspection.metadata.robot_pose.position.x,
                    "y": inspection.metadata.robot_pose.position.y,
                    "z": inspection.metadata.robot_pose.position.z,
                },
                "orientation": str(
                    inspection.metadata.robot_pose.orientation.to_quat_array()
                ),
            },
            "target_position": {
                "x": inspection.metadata.target_position.x,
                "y": inspection.metadata.target_position.y,
                "z": inspection.metadata.target_position.z,
            },
            "timestamp": inspection.metadata.start_time.strftime(
                "%Y-%m-%dT%H:%M:%S.%f"
            ),
        },
        "data_files": [
            {
                "folder": f"/{get_foldername(mission=mission)}",
                "file_name": filename,
            }
        ],
    }

    if isinstance(inspection.metadata, AcousticMeasurementMetadata):
        data["additional_meta"]["acoustic_result"] = {
            "snr_value": inspection.metadata.snr_value,
            "leak_rate": inspection.metadata.leak_rate,
            "leak_rate_unit": inspection.metadata.leak_rate_unit,
            "sound_pressure_level_at_sensor_db": inspection.metadata.sound_pressure_level_at_sensor_db,  # noqa: E501
            "sound_pressure_level_at_source_db": inspection.metadata.sound_pressure_level_at_source_db,  # noqa: E501
            "distance_to_source": inspection.metadata.distance_to_source,
            "result": inspection.metadata.result,
            "frequency_from": inspection.metadata.frequency_from,
            "frequency_to": inspection.metadata.frequency_to,
        }

    return json.dumps(data, indent=4).encode()


def get_filename(inspection: Inspection) -> str:
    utc_time: str = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    tag: str = inspection.metadata.tag_id if inspection.metadata.tag_id else "no-tag"
    inspection_type: str = type(inspection).__name__
    inspection_description: str = (
        inspection.metadata.inspection_description.replace(" ", "-")
        if inspection.metadata.inspection_description
        else "NA"
    )
    return f"{tag}__{inspection_type}__{inspection_description}__{utc_time}"


def get_foldername(mission: Mission) -> str:
    utc_date: str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    mission_name: str = mission.name.replace(" ", "-")
    return f"{utc_date}__{settings.PLANT_SHORT_NAME}__{mission_name}__{mission.id}"
