import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Type
from uuid import uuid4

from pydantic import BaseModel, Field

from isar.apis.models.models import InputPose, InputPosition
from isar.config.settings import settings
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import (
    TASKS,
    AcousticDetectionType,
    InspectionTask,
    RecordAudio,
    ReturnToHome,
    Roi,
    TakeAcousticMeasurement,
    TakeCO2Measurement,
    TakeImage,
    TakeThermalImage,
    TakeThermalVideo,
    TakeVideo,
    ZoomDescription,
)


class InspectionTypes(str, Enum):
    image = "Image"
    thermal_image = "ThermalImage"
    video = "Video"
    thermal_video = "ThermalVideo"
    audio = "Audio"
    co2_measurement = "CO2Measurement"
    acoustic_measurement = "AcousticMeasurement"


class TaskType(str, Enum):
    Inspection = "inspection"
    ReturnToHome = "return_to_home"


class AcousticInspectionParameters(BaseModel):
    frequency_from: float
    frequency_to: float
    snr_value_threshold: float
    detection_type: AcousticDetectionType
    roi: Roi | None = None


class StartMissionInspectionDefinition(BaseModel):
    type: InspectionTypes = Field(default=InspectionTypes.image)
    inspection_target: InputPosition
    inspection_description: str | None = None
    duration: float | None = None
    acoustic: AcousticInspectionParameters | None = None
    analysis_types: list[str] | None = Field(default=None)


class StartMissionTaskDefinition(BaseModel):
    id: str | None = None
    type: TaskType = Field(default=TaskType.Inspection)
    pose: InputPose
    inspection: StartMissionInspectionDefinition | None = None
    tag: str | None = None
    zoom: ZoomDescription | None = None


class StartMissionDefinition(BaseModel):
    id: str | None = None
    tasks: List[StartMissionTaskDefinition]
    name: str | None = None
    start_pose: InputPose | None = None


class StopMissionDefinition(BaseModel):
    mission_id: str | None = None


class MissionFormatError(Exception):
    pass


def to_isar_mission(
    start_mission_definition: StartMissionDefinition,
) -> Mission:
    isar_tasks: List[TASKS] = []

    for task_definition in start_mission_definition.tasks:
        task: TASKS = to_isar_task(task_definition)
        isar_tasks.append(task)

    if not isar_tasks:
        raise MissionFormatError("Mission does not contain any valid tasks")

    isar_mission_name: str = (
        start_mission_definition.name
        if start_mission_definition.name
        else _build_mission_name()
    )

    start_pose = None
    if start_mission_definition.start_pose:
        start_pose = start_mission_definition.start_pose.to_alitra_pose()

    id = start_mission_definition.id if start_mission_definition.id else str(uuid4())

    return Mission(
        id=id,
        tasks=isar_tasks,
        name=isar_mission_name,
        start_pose=start_pose,
    )


def to_isar_task(task_definition: StartMissionTaskDefinition) -> TASKS:
    if task_definition.type == TaskType.Inspection:
        return to_inspection_task(task_definition)
    elif task_definition.type == TaskType.ReturnToHome:
        return ReturnToHome()
    else:
        raise MissionFormatError(
            f"Failed to create task: '{task_definition.type}' is not a valid"
        )


@dataclass(frozen=True)
class _InspectionSpec:
    cls: Type[InspectionTask]
    needs_target: bool = True
    needs_zoom: bool = False
    needs_duration: bool = False
    needs_acoustic_params: bool = False


_INSPECTION_SPECS: dict[InspectionTypes, _InspectionSpec] = {
    InspectionTypes.image: _InspectionSpec(TakeImage, needs_zoom=True),
    InspectionTypes.thermal_image: _InspectionSpec(TakeThermalImage, needs_zoom=True),
    InspectionTypes.video: _InspectionSpec(
        TakeVideo, needs_zoom=True, needs_duration=True
    ),
    InspectionTypes.thermal_video: _InspectionSpec(
        TakeThermalVideo, needs_zoom=True, needs_duration=True
    ),
    InspectionTypes.audio: _InspectionSpec(RecordAudio, needs_duration=True),
    InspectionTypes.co2_measurement: _InspectionSpec(
        TakeCO2Measurement, needs_target=False
    ),
    InspectionTypes.acoustic_measurement: _InspectionSpec(
        TakeAcousticMeasurement, needs_acoustic_params=True
    ),
}


def to_inspection_task(task_definition: StartMissionTaskDefinition) -> TASKS:
    if task_definition.inspection is None:
        raise ValueError("Inspection in task definition was None")

    inspection_definition = task_definition.inspection
    spec = _INSPECTION_SPECS.get(inspection_definition.type)
    if spec is None:
        raise ValueError(
            f"Inspection type '{inspection_definition.type}' not supported"
        )

    if spec.needs_duration and inspection_definition.duration is None:
        raise ValueError(
            f"No duration given to {inspection_definition.type.value} inspection task"
        )

    kwargs: dict = {
        "id": task_definition.id if task_definition.id else str(uuid4()),
        "robot_pose": task_definition.pose.to_alitra_pose(),
        "tag_id": task_definition.tag,
        "inspection_description": inspection_definition.inspection_description,
        "analysis_types": inspection_definition.analysis_types,
    }
    if spec.needs_target:
        kwargs["target"] = inspection_definition.inspection_target.to_alitra_position()
    if spec.needs_zoom:
        kwargs["zoom"] = task_definition.zoom
    if spec.needs_duration:
        kwargs["duration"] = inspection_definition.duration
    if spec.needs_acoustic_params:
        acoustic = inspection_definition.acoustic
        if acoustic is None:
            raise ValueError(
                f"No acoustic parameters given to "
                f"{inspection_definition.type.value} inspection task"
            )
        kwargs["frequency_from"] = acoustic.frequency_from
        kwargs["frequency_to"] = acoustic.frequency_to
        kwargs["snr_value_threshold"] = acoustic.snr_value_threshold
        kwargs["detection_type"] = acoustic.detection_type
        kwargs["roi"] = acoustic.roi

    return spec.cls(**kwargs)


def _build_mission_name() -> str:
    return f"{settings.PLANT_SHORT_NAME}{settings.ROBOT_NAME}{int(time.time())}"
