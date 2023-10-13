import time
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from alitra import Position
from pydantic import BaseModel, Field

from isar.apis.models.models import InputPose, InputPosition
from isar.config.settings import settings
from isar.mission_planner.mission_planner_interface import MissionPlannerError
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.step import (
    DockingProcedure,
    DriveToPose,
    Localize,
    RecordAudio,
    STEPS,
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
    DriveTo: str = "drive_to"
    Localization: str = "localization"
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
    inspections: List[StartMissionInspectionDefinition]
    tag: Optional[str] = None
    id: Optional[str] = None


class StartMissionDefinition(BaseModel):
    tasks: List[StartMissionTaskDefinition]
    id: Optional[str] = None
    name: Optional[str] = None


def to_isar_mission(mission_definition: StartMissionDefinition) -> Mission:
    isar_tasks: List[Task] = []
    all_steps_in_mission: List[STEPS] = []

    for task in mission_definition.tasks:
        steps: List[STEPS] = generate_steps(task)
        all_steps_in_mission.extend(steps)

        isar_task: Task = Task(steps=steps, tag_id=task.tag)
        if task.id:
            isar_task.id = task.id
        isar_tasks.append(isar_task)

    if not isar_tasks:
        raise MissionPlannerError("Mission does not contain any valid tasks")

    check_for_duplicate_ids(isar_tasks)
    check_for_duplicate_ids(all_steps_in_mission)

    isar_mission: Mission = Mission(tasks=isar_tasks)

    if mission_definition.name:
        isar_mission.name = mission_definition.name
    else:
        isar_mission.name = _build_mission_name()

    if mission_definition.id:
        isar_mission.id = mission_definition.id

    return isar_mission


def check_for_duplicate_ids(items: Union[List[Task], List[STEPS]]):
    duplicate_ids = get_duplicate_ids(items=items)
    if len(duplicate_ids) > 0:
        raise MissionPlannerError(
            f"Failed to create as there were duplicate IDs which is not allowed "
            f"({duplicate_ids})"
        )


def generate_steps(task) -> List[STEPS]:
    steps: List[STEPS] = []
    try:
        match task.type:
            case TaskType.Inspection:
                steps.extend(generate_steps_for_inspection_task(task=task))
            case TaskType.DriveTo:
                steps.append(generate_steps_for_drive_to_task(task=task))
            case TaskType.Localization:
                steps.append(generate_steps_for_localization_task(task=task))
            case TaskType.Dock:
                steps.append(generate_steps_for_dock_task())
    except ValueError as e:
        raise MissionPlannerError(f"Failed to create task: {str(e)}")

    return steps


def generate_steps_for_inspection_task(task: StartMissionTaskDefinition) -> List[STEPS]:
    drive_step: DriveToPose = DriveToPose(pose=task.pose.to_alitra_pose())

    inspection_steps: List[STEPS] = [
        create_inspection_step(
            inspection_type=inspection.type,
            duration=inspection.duration,
            target=inspection.inspection_target.to_alitra_position(),
            tag_id=task.tag,
            metadata=inspection.metadata,
            id=inspection.id,
        )
        for inspection in task.inspections
    ]

    return [drive_step, *inspection_steps]


def generate_steps_for_drive_to_task(task: StartMissionTaskDefinition) -> DriveToPose:
    return DriveToPose(pose=task.pose.to_alitra_pose())


def generate_steps_for_localization_task(task: StartMissionTaskDefinition) -> Localize:
    return Localize(localization_pose=task.pose.to_alitra_pose())


def generate_steps_for_dock_task() -> DockingProcedure:
    return DockingProcedure(behavior="dock")


def create_inspection_step(
    inspection_type: InspectionTypes,
    duration: float,
    target: Position,
    tag_id: Optional[str],
    metadata: Optional[dict],
    id: Optional[str],
) -> STEPS:
    inspection_step_dict: Dict[str, Any] = {
        InspectionTypes.image.value: TakeImage(target=target),
        InspectionTypes.video.value: TakeVideo(target=target, duration=duration),
        InspectionTypes.thermal_image.value: TakeThermalImage(target=target),
        InspectionTypes.thermal_video.value: TakeThermalVideo(
            target=target, duration=duration
        ),
        InspectionTypes.audio.value: RecordAudio(target=target, duration=duration),
    }

    if inspection_type not in inspection_step_dict:
        raise ValueError(f"Inspection type '{inspection_type}' not supported")
    else:
        inspection_step = inspection_step_dict[inspection_type]

    if tag_id:
        inspection_step.tag_id = tag_id
    if metadata:
        inspection_step.metadata = metadata
    if id:
        inspection_step.id = id

    return inspection_step


def get_duplicate_ids(items: Union[List[Task], List[STEPS]]) -> List[str]:
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
