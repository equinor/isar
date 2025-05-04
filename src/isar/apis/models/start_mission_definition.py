import time
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from isar.apis.models.models import InputPose, InputPosition
from isar.config.settings import settings
from isar.mission_planner.mission_planner_interface import MissionPlannerError
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import (
    TASKS,
    RecordAudio,
    ReturnToHome,
    TakeGasMeasurement,
    TakeImage,
    TakeThermalImage,
    TakeThermalVideo,
    TakeVideo,
    ZoomDescription,
)
from robot_interface.utilities.uuid_string_factory import uuid4_string


class InspectionTypes(str, Enum):
    image = "Image"
    thermal_image = "ThermalImage"
    video = "Video"
    thermal_video = "ThermalVideo"
    audio = "Audio"
    gas_measurement = "GasMeasurement"


class TaskType(str, Enum):
    Inspection = "inspection"
    ReturnToHome = "return_to_home"


class StartMissionInspectionDefinition(BaseModel):
    type: InspectionTypes = Field(default=InspectionTypes.image)
    inspection_target: InputPosition
    inspection_description: Optional[str] = None
    duration: Optional[float] = None


class StartMissionTaskDefinition(BaseModel):
    id: Optional[str] = None
    type: TaskType = Field(default=TaskType.Inspection)
    pose: InputPose
    inspection: Optional[StartMissionInspectionDefinition] = None
    tag: Optional[str] = None
    zoom: Optional[ZoomDescription] = None


class StartMissionDefinition(BaseModel):
    tasks: List[StartMissionTaskDefinition]
    name: Optional[str] = None
    start_pose: Optional[InputPose] = None


def to_isar_mission(
    start_mission_definition: StartMissionDefinition,
) -> Mission:
    isar_tasks: List[TASKS] = []

    for task_definition in start_mission_definition.tasks:
        task: TASKS = to_isar_task(task_definition)
        isar_tasks.append(task)

    if not isar_tasks:
        raise MissionPlannerError("Mission does not contain any valid tasks")

    isar_mission_name: str = (
        start_mission_definition.name
        if start_mission_definition.name
        else _build_mission_name()
    )

    start_pose = None
    if start_mission_definition.start_pose:
        start_pose = start_mission_definition.start_pose.to_alitra_pose()

    return Mission(
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
        raise MissionPlannerError(
            f"Failed to create task: '{task_definition.type}' is not a valid"
        )


def to_inspection_task(task_definition: StartMissionTaskDefinition) -> TASKS:
    inspection_definition = task_definition.inspection

    if inspection_definition.type == InspectionTypes.image:
        return TakeImage(
            id=task_definition.id if task_definition.id else uuid4_string(),
            robot_pose=task_definition.pose.to_alitra_pose(),
            tag_id=task_definition.tag,
            inspection_description=task_definition.inspection.inspection_description,
            target=task_definition.inspection.inspection_target.to_alitra_position(),
            zoom=task_definition.zoom,
        )
    elif inspection_definition.type == InspectionTypes.video:
        return TakeVideo(
            id=task_definition.id if task_definition.id else uuid4_string(),
            robot_pose=task_definition.pose.to_alitra_pose(),
            tag_id=task_definition.tag,
            inspection_description=task_definition.inspection.inspection_description,
            target=task_definition.inspection.inspection_target.to_alitra_position(),
            duration=inspection_definition.duration,
            zoom=task_definition.zoom,
        )
    elif inspection_definition.type == InspectionTypes.thermal_image:
        return TakeThermalImage(
            id=task_definition.id if task_definition.id else uuid4_string(),
            robot_pose=task_definition.pose.to_alitra_pose(),
            tag_id=task_definition.tag,
            inspection_description=task_definition.inspection.inspection_description,
            target=task_definition.inspection.inspection_target.to_alitra_position(),
            zoom=task_definition.zoom,
        )
    elif inspection_definition.type == InspectionTypes.thermal_video:
        return TakeThermalVideo(
            id=task_definition.id if task_definition.id else uuid4_string(),
            robot_pose=task_definition.pose.to_alitra_pose(),
            tag_id=task_definition.tag,
            inspection_description=task_definition.inspection.inspection_description,
            target=task_definition.inspection.inspection_target.to_alitra_position(),
            duration=inspection_definition.duration,
            zoom=task_definition.zoom,
        )
    elif inspection_definition.type == InspectionTypes.audio:
        return RecordAudio(
            id=task_definition.id if task_definition.id else uuid4_string(),
            robot_pose=task_definition.pose.to_alitra_pose(),
            tag_id=task_definition.tag,
            inspection_description=task_definition.inspection.inspection_description,
            target=task_definition.inspection.inspection_target.to_alitra_position(),
            duration=inspection_definition.duration,
        )
    elif inspection_definition.type == InspectionTypes.gas_measurement:
        return TakeGasMeasurement(
            id=task_definition.id if task_definition.id else uuid4_string(),
            robot_pose=task_definition.pose.to_alitra_pose(),
            tag_id=task_definition.tag,
            inspection_description=task_definition.inspection.inspection_description,
        )
    else:
        raise ValueError(
            f"Inspection type '{inspection_definition.type}' not supported"
        )


def _build_mission_name() -> str:
    return f"{settings.PLANT_SHORT_NAME}{settings.ROBOT_NAME}{int(time.time())}"
