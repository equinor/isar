from enum import Enum
from typing import List, Optional, Union

from alitra import Position
from pydantic import BaseModel, Field

from isar.apis.models.models import InputPose, InputPosition
from isar.mission_planner.mission_planner_interface import MissionPlannerError
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.step import (
    DriveToPose,
    RecordAudio,
    STEPS,
    TakeImage,
    TakeThermalImage,
    TakeThermalVideo,
    TakeVideo,
)
from robot_interface.models.mission.task import Task


class InspectionTypes(str, Enum):
    image = "Image"
    thermal_image = "ThermalImage"
    video = "Video"
    thermal_video = "ThermalVideo"
    audio = "Audio"


class StartMissionInspectionDefinition(BaseModel):
    type: InspectionTypes = Field(default=InspectionTypes.image)
    inspection_target: InputPosition
    analysis_types: Optional[List]
    duration: Optional[float]
    metadata: Optional[dict]
    id: Optional[str]


class StartMissionTaskDefinition(BaseModel):
    pose: InputPose
    inspections: List[StartMissionInspectionDefinition]
    tag: Optional[str]
    id: Optional[str]


class StartMissionDefinition(BaseModel):
    tasks: List[StartMissionTaskDefinition]
    id: Optional[str]


def to_isar_mission(mission_definition: StartMissionDefinition) -> Mission:
    isar_tasks: List[Task] = []
    all_inspection_steps: List[STEPS] = []
    duplicate_ids: List[str] = []

    for task in mission_definition.tasks:
        try:
            tag_id: Optional[str] = task.tag
            drive_step: DriveToPose = DriveToPose(pose=task.pose.to_alitra_pose())
            inspection_steps: List[STEPS] = [
                create_inspection_step(
                    inspection_type=inspection.type,
                    duration=inspection.duration,
                    target=inspection.inspection_target.to_alitra_position(),
                    tag_id=tag_id,
                    analysis=inspection.analysis_types,
                    metadata=inspection.metadata,
                    id=inspection.id,
                )
                for inspection in task.inspections
            ]
        except ValueError as e:
            raise MissionPlannerError(f"Failed to create task: {str(e)}")

        duplicate_ids = get_duplicate_ids(items=inspection_steps)
        if len(duplicate_ids) > 0:
            raise MissionPlannerError(
                f"Failed to create task: Duplicate step IDs are not allowed ({duplicate_ids})"
            )
        all_inspection_steps.extend(inspection_steps)

        isar_task: Task = Task(steps=[drive_step, *inspection_steps], tag_id=tag_id)
        if task.id:
            isar_task.id = task.id
        isar_tasks.append(isar_task)

    if not isar_tasks:
        raise MissionPlannerError("Mission does not contain any valid tasks")

    duplicate_ids = get_duplicate_ids(items=isar_tasks)
    if len(duplicate_ids) > 0:
        raise MissionPlannerError(
            f"Failed to create mission: Duplicate task IDs are not allowed ({duplicate_ids})"
        )

    duplicate_ids = get_duplicate_ids(items=all_inspection_steps)
    if len(duplicate_ids) > 0:
        raise MissionPlannerError(
            f"Failed to create task: Duplicate step IDs are not allowed ({duplicate_ids})"
        )

    isar_mission: Mission = Mission(tasks=isar_tasks)

    return isar_mission


def create_inspection_step(
    inspection_type: InspectionTypes,
    duration: float,
    target: Position,
    analysis: Optional[List],
    tag_id: Optional[str],
    metadata: Optional[dict],
    id: Optional[str],
) -> STEPS:
    inspection_step: STEPS
    if inspection_type == InspectionTypes.image.value:
        inspection_step = TakeImage(target=target)
    elif inspection_type == InspectionTypes.video.value:
        inspection_step = TakeVideo(target=target, duration=duration)
    elif inspection_type == InspectionTypes.thermal_image.value:
        inspection_step = TakeThermalImage(target=target)
    elif inspection_type == InspectionTypes.thermal_video.value:
        inspection_step = TakeThermalVideo(target=target, duration=duration)
    elif inspection_type == InspectionTypes.audio.value:
        inspection_step = RecordAudio(target=target, duration=duration)
    else:
        raise ValueError(f"Inspection type '{inspection_type}' not supported")

    if tag_id:
        inspection_step.tag_id = tag_id
    if analysis:
        inspection_step.analysis = analysis
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
