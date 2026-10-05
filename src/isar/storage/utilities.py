from datetime import UTC, datetime
from pathlib import Path

from isar.config.settings import settings
from isar.storage.storage_interface import StorageException
from robot_interface.models.inspection.inspection import (
    Inspection,
    InspectionBlob,
    InspectionValue,
)
from robot_interface.models.mission.mission import Mission


def inspection_bytes(inspection: InspectionBlob | InspectionValue) -> bytes:
    if isinstance(inspection, InspectionValue):
        return inspection.model_dump_json().encode("utf-8")
    if inspection.data is None:
        raise StorageException("Nothing to store. The inspection data is empty")
    return inspection.data


def construct_path(inspection: Inspection, mission: Mission) -> Path:
    folder: Path = Path(get_foldername(mission=mission))
    filename: str = get_filename(inspection=inspection)

    return folder.joinpath(f"{filename}.{inspection.metadata.file_type}")


def get_filename(inspection: Inspection) -> str:
    utc_time: str = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    tag: str = inspection.metadata.tag_id if inspection.metadata.tag_id else "no-tag"
    inspection_type: str = type(inspection).__name__
    inspection_description: str = (
        inspection.metadata.inspection_description.replace(" ", "-")
        if inspection.metadata.inspection_description
        else "NA"
    )
    return f"{tag}__{inspection_type}__{inspection_description}__{utc_time}"


def get_foldername(mission: Mission) -> str:
    utc_date: str = datetime.now(UTC).strftime("%Y-%m-%d")
    mission_name: str = mission.name.replace(" ", "-")
    return f"{utc_date}__{settings.PLANT_SHORT_NAME}__{mission_name}__{mission.id}"
