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
    DockingProcedure,
    Localize,
    RecordAudio,
    ReturnToHome,
    TakeImage,
    TakeThermalImage,
    TakeThermalVideo,
    TakeVideo,
    TakeGasMeasurement,
    ZoomDescription,
)


class InspectionTypes(str, Enum):
    image = "Image"
    thermal_image = "ThermalImage"
    video = "Video"
    thermal_video = "ThermalVideo"
    audio = "Audio"
    gas_measurement = "GasMeasurement"


class TaskType(str, Enum):
    Inspection = "inspection"
    Localization = "localization"
    ReturnToHome = "return_to_home"
    Dock = "dock"


class StartMissionInspectionDefinition(BaseModel):
    type: InspectionTypes = Field(default=InspectionTypes.image)
    inspection_target: InputPosition
    analysis_type: Optional[str] = None
    duration: Optional[float] = None
    metadata: Optional[dict] = None


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
    dock: Optional[bool] = Field(default=False)
    undock: Optional[bool] = Field(default=False)


def to_isar_mission(
    start_mission_definition: StartMissionDefinition,
    return_pose: Optional[InputPose] = None,
) -> Mission:
    isar_tasks: List[TASKS] = []

    for task_definition in start_mission_definition.tasks:
        task: TASKS = to_isar_task(task_definition)
        isar_tasks.append(task)

    if return_pose:
        isar_tasks.append(ReturnToHome(pose=return_pose.to_alitra_pose()))

    if not isar_tasks:
        raise MissionPlannerError("Mission does not contain any valid tasks")

    isar_mission_name: str
    if start_mission_definition.name:
        isar_mission_name = start_mission_definition.name
    else:
        isar_mission_name = _build_mission_name()

    start_pose = None
    if start_mission_definition.start_pose:
        start_pose = start_mission_definition.start_pose.to_alitra_pose()

    return Mission(
        tasks=isar_tasks,
        name=isar_mission_name,
        start_pose=start_pose,
        dock=start_mission_definition.dock,
        undock=start_mission_definition.undock,
    )


def to_isar_task(task_definition: StartMissionTaskDefinition) -> TASKS:
    if task_definition.type == TaskType.Inspection:
        return to_inspection_task(task_definition)
    elif task_definition.type == TaskType.Localization:
        return to_localization_task(task_definition)
    elif task_definition.type == TaskType.ReturnToHome:
        return create_return_to_home_task(task_definition)
    elif task_definition.type == TaskType.Dock:
        return create_dock_task()
    else:
        raise MissionPlannerError(
            f"Failed to create task: '{task_definition.type}' is not a valid"
        )


def to_inspection_task(task_definition: StartMissionTaskDefinition) -> TASKS:
    inspection_definition = task_definition.inspection

    if inspection_definition.type == InspectionTypes.image:
        if task_definition.id:
            return TakeImage(
                id=task_definition.id,
                robot_pose=task_definition.pose.to_alitra_pose(),
                tag_id=task_definition.tag,
                target=task_definition.inspection.inspection_target.to_alitra_position(),
                metadata=task_definition.inspection.metadata,
                zoom=task_definition.zoom,
            )
        else:
            return TakeImage(
                robot_pose=task_definition.pose.to_alitra_pose(),
                tag_id=task_definition.tag,
                target=task_definition.inspection.inspection_target.to_alitra_position(),
                metadata=task_definition.inspection.metadata,
                zoom=task_definition.zoom,
            )
    elif inspection_definition.type == InspectionTypes.video:
        if task_definition.id:
            return TakeVideo(
                id=task_definition.id,
                robot_pose=task_definition.pose.to_alitra_pose(),
                tag_id=task_definition.tag,
                target=task_definition.inspection.inspection_target.to_alitra_position(),
                duration=inspection_definition.duration,
                metadata=task_definition.inspection.metadata,
                zoom=task_definition.zoom,
            )
        else:
            return TakeVideo(
                robot_pose=task_definition.pose.to_alitra_pose(),
                tag_id=task_definition.tag,
                target=task_definition.inspection.inspection_target.to_alitra_position(),
                duration=inspection_definition.duration,
                metadata=task_definition.inspection.metadata,
                zoom=task_definition.zoom,
            )
    elif inspection_definition.type == InspectionTypes.thermal_image:
        if task_definition.id:
            return TakeThermalImage(
                id=task_definition.id,
                robot_pose=task_definition.pose.to_alitra_pose(),
                tag_id=task_definition.tag,
                target=task_definition.inspection.inspection_target.to_alitra_position(),
                metadata=task_definition.inspection.metadata,
                zoom=task_definition.zoom,
            )
        else:
            return TakeThermalImage(
                robot_pose=task_definition.pose.to_alitra_pose(),
                tag_id=task_definition.tag,
                target=task_definition.inspection.inspection_target.to_alitra_position(),
                metadata=task_definition.inspection.metadata,
                zoom=task_definition.zoom,
            )
    elif inspection_definition.type == InspectionTypes.thermal_video:
        if task_definition.id:
            return TakeThermalVideo(
                id=task_definition.id,
                robot_pose=task_definition.pose.to_alitra_pose(),
                tag_id=task_definition.tag,
                target=task_definition.inspection.inspection_target.to_alitra_position(),
                duration=inspection_definition.duration,
                metadata=task_definition.inspection.metadata,
                zoom=task_definition.zoom,
            )
        else:
            return TakeThermalVideo(
                robot_pose=task_definition.pose.to_alitra_pose(),
                tag_id=task_definition.tag,
                target=task_definition.inspection.inspection_target.to_alitra_position(),
                duration=inspection_definition.duration,
                metadata=task_definition.inspection.metadata,
                zoom=task_definition.zoom,
            )
    elif inspection_definition.type == InspectionTypes.audio:
        if task_definition.id:
            return RecordAudio(
                id=task_definition.id,
                robot_pose=task_definition.pose.to_alitra_pose(),
                tag_id=task_definition.tag,
                target=task_definition.inspection.inspection_target.to_alitra_position(),
                duration=inspection_definition.duration,
                metadata=task_definition.inspection.metadata,
            )
        else:
            return RecordAudio(
                robot_pose=task_definition.pose.to_alitra_pose(),
                tag_id=task_definition.tag,
                target=task_definition.inspection.inspection_target.to_alitra_position(),
                duration=inspection_definition.duration,
                metadata=task_definition.inspection.metadata,
            )
    elif inspection_definition.type == InspectionTypes.gas_measurement:
        if task_definition.id:
            return TakeGasMeasurement(
                id=task_definition.id,
                robot_pose=task_definition.pose.to_alitra_pose(),
                tag_id=task_definition.tag,
                metadata=task_definition.inspection.metadata,
            )
        else:
            return TakeGasMeasurement(
                robot_pose=task_definition.pose.to_alitra_pose(),
                tag_id=task_definition.tag,
                metadata=task_definition.inspection.metadata,
            )
    else:
        raise ValueError(
            f"Inspection type '{inspection_definition.type}' not supported"
        )


def to_localization_task(task_definition: StartMissionTaskDefinition) -> Localize:
    return Localize(localization_pose=task_definition.pose.to_alitra_pose())


def create_return_to_home_task(
    task_definition: StartMissionTaskDefinition,
) -> ReturnToHome:
    return ReturnToHome(pose=task_definition.pose.to_alitra_pose())


def create_dock_task() -> DockingProcedure:
    return DockingProcedure(behavior="dock")


def _build_mission_name() -> str:
    return f"{settings.PLANT_SHORT_NAME}{settings.ROBOT_NAME}{int(time.time())}"
