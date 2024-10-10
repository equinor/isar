import time
from enum import Enum
from typing import Any, Dict, List, Optional

from alitra import Frame, Orientation, Pose, Position
from pydantic import BaseModel, Field

from isar.apis.models.models import InputPose, InputPosition
from isar.config.settings import settings
from isar.mission_planner.mission_planner_interface import MissionPlannerError
from robot_interface.models.inspection.inspection import Inspection, InspectionMetadata
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
)
from robot_interface.models.mission.task import Task


class InspectionTypes(str, Enum):
    image: str = "Image"
    thermal_image: str = "ThermalImage"
    video: str = "Video"
    thermal_video: str = "ThermalVideo"
    audio: str = "Audio"


class TaskType(str, Enum):
    Inspection: str = "inspection"
    Localization: str = "localization"
    ReturnToHome: str = "return_to_home"
    Dock: str = "dock"


class StartMissionInspectionDefinition(BaseModel):
    type: InspectionTypes = Field(default=InspectionTypes.image)
    inspection_target: InputPosition
    analysis_type: Optional[str] = None
    duration: Optional[float] = None
    metadata: Optional[dict] = None
    id: Optional[str] = None


class StartMissionTaskDefinition(BaseModel):
    type: TaskType = Field(default=TaskType.Inspection)
    pose: InputPose
    inspection: StartMissionInspectionDefinition
    tag: Optional[str] = None
    id: Optional[str] = None


class StartMissionDefinition(BaseModel):
    tasks: List[StartMissionTaskDefinition]
    id: Optional[str] = None
    name: Optional[str] = None
    start_pose: Optional[InputPose] = None
    dock: Optional[bool] = None
    undock: Optional[bool] = None


def to_isar_mission(start_mission_definition: StartMissionDefinition) -> Mission:
    isar_tasks: List[TASKS] = []

    for start_mission_task_definition in start_mission_definition.tasks:
        task: TASKS = create_isar_task(start_mission_task_definition)
        if start_mission_task_definition.id:
            task.id = start_mission_task_definition.id
        isar_tasks.append(task)

    if not isar_tasks:
        raise MissionPlannerError("Mission does not contain any valid tasks")

    check_for_duplicate_ids(isar_tasks)

    isar_mission: Mission = Mission(tasks=isar_tasks)

    isar_mission.dock = start_mission_definition.dock
    isar_mission.undock = start_mission_definition.undock

    if start_mission_definition.name:
        isar_mission.name = start_mission_definition.name
    else:
        isar_mission.name = _build_mission_name()

    if start_mission_definition.id:
        isar_mission.id = start_mission_definition.id

    if start_mission_definition.start_pose:
        input_pose: InputPose = start_mission_definition.start_pose
        input_frame: Frame = Frame(name=input_pose.frame_name)
        input_position: Position = Position(
            input_pose.position.x,
            input_pose.position.y,
            input_pose.position.z,
            input_frame,
        )
        input_orientation: Orientation = Orientation(
            input_pose.orientation.x,
            input_pose.orientation.y,
            input_pose.orientation.z,
            input_pose.orientation.w,
            input_frame,
        )
        isar_mission.start_pose = Pose(
            position=input_position, orientation=input_orientation, frame=input_frame
        )

    return isar_mission


def check_for_duplicate_ids(items: List[TASKS]):
    duplicate_ids = get_duplicate_ids(items=items)
    if len(duplicate_ids) > 0:
        raise MissionPlannerError(
            f"Failed to create as there were duplicate IDs which is not allowed "
            f"({duplicate_ids})"
        )


def create_isar_task(start_mission_task_definition) -> TASKS:

    if start_mission_task_definition.type == TaskType.Inspection:
        return create_inspection_task(start_mission_task_definition)
    elif start_mission_task_definition.type == TaskType.Localization:
        return create_localization_task(start_mission_task_definition)
    elif start_mission_task_definition.type == TaskType.ReturnToHome:
        return create_return_to_home_task(start_mission_task_definition)
    elif start_mission_task_definition.type == TaskType.Dock:
        return create_dock_task()
    else:
        raise MissionPlannerError(
            f"Failed to create task: '{start_mission_task_definition.type}' is not a valid"
        )


def create_inspection_task(
    start_mission_task_definition: StartMissionTaskDefinition,
) -> TASKS:

    if start_mission_task_definition.inspection.type == InspectionTypes.image:
        return TakeImage(
            target=start_mission_task_definition.inspection.inspection_target.to_alitra_position(),
            tag_id=start_mission_task_definition.tag,
            robot_pose=start_mission_task_definition.pose.to_alitra_pose(),
            metadata=start_mission_task_definition.inspection.metadata,
        )
    elif start_mission_task_definition.inspection.type == InspectionTypes.video:
        return TakeVideo(
            target=start_mission_task_definition.inspection.inspection_target.to_alitra_position(),
            duration=start_mission_task_definition.inspection.duration,
            tag_id=start_mission_task_definition.tag,
            robot_pose=start_mission_task_definition.pose.to_alitra_pose(),
            metadata=start_mission_task_definition.inspection.metadata,
        )

    elif start_mission_task_definition.inspection.type == InspectionTypes.thermal_image:
        return TakeThermalImage(
            target=start_mission_task_definition.inspection.inspection_target.to_alitra_position(),
            tag_id=start_mission_task_definition.tag,
            robot_pose=start_mission_task_definition.pose.to_alitra_pose(),
            metadata=start_mission_task_definition.inspection.metadata,
        )

    elif start_mission_task_definition.inspection.type == InspectionTypes.thermal_video:
        return TakeThermalVideo(
            target=start_mission_task_definition.inspection.inspection_target.to_alitra_position(),
            duration=start_mission_task_definition.inspection.duration,
            tag_id=start_mission_task_definition.tag,
            robot_pose=start_mission_task_definition.pose.to_alitra_pose(),
            metadata=start_mission_task_definition.inspection.metadata,
        )

    elif start_mission_task_definition.inspection.type == InspectionTypes.audio:
        return RecordAudio(
            target=start_mission_task_definition.inspection.inspection_target.to_alitra_position(),
            duration=start_mission_task_definition.inspection.duration,
            tag_id=start_mission_task_definition.tag,
            robot_pose=start_mission_task_definition.pose.to_alitra_pose(),
            metadata=start_mission_task_definition.inspection.metadata,
        )
    else:
        raise ValueError(
            f"Inspection type '{start_mission_task_definition.inspection.type}' not supported"
        )


def create_localization_task(
    start_mission_task_definition: StartMissionTaskDefinition,
) -> Localize:
    return Localize(
        localization_pose=start_mission_task_definition.pose.to_alitra_pose()
    )


def create_return_to_home_task(
    start_mission_task_definition: StartMissionTaskDefinition,
) -> ReturnToHome:
    return ReturnToHome(pose=start_mission_task_definition.pose.to_alitra_pose())


def create_dock_task() -> DockingProcedure:
    return DockingProcedure(behavior="dock")


def get_duplicate_ids(items: List[TASKS]) -> List[str]:
    unique_ids: List[str] = []
    duplicate_ids: List[str] = []
    for item in items:
        id: str = item.id
        if id not in unique_ids:
            unique_ids.append(id)
        else:
            duplicate_ids.append(id)

    return duplicate_ids


def _build_mission_name() -> str:
    return f"{settings.PLANT_SHORT_NAME}{settings.ROBOT_NAME}{int(time.time())}"
