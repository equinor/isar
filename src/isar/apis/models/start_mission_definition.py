from enum import Enum
from typing import List, Optional

from alitra import Position
from pydantic import BaseModel, Field

from isar.apis.models.models import InputPose, InputPosition
from isar.mission_planner.mission_planner_interface import MissionPlannerError
from isar.models.mission.mission import Mission, Task
from robot_interface.models.mission.step import (
    STEPS,
    DriveToPose,
    TakeImage,
    TakeThermalImage,
    TakeThermalVideo,
    TakeVideo,
)


class InspectionTypes(str, Enum):
    image = "Image"
    thermal_image = "ThermalImage"
    video = "Video"
    thermal_video = "ThermalVideo"


class StartMissionInspectionDefinition(BaseModel):
    type: InspectionTypes = Field(default=InspectionTypes.image)
    inspection_target: InputPosition
    analysis_types: Optional[List]
    duration: Optional[float]
    metadata: Optional[dict]


class StartMissionTaskDefinition(BaseModel):
    pose: InputPose
    tag: Optional[str]
    inspections: List[StartMissionInspectionDefinition]


class StartMissionDefinition(BaseModel):
    tasks: List[StartMissionTaskDefinition]


def to_isar_mission(mission_definition: StartMissionDefinition) -> Mission:
    isar_tasks: List[Task] = []

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
                )
                for inspection in task.inspections
            ]
        except ValueError as e:
            raise MissionPlannerError(f"Failed to create task: {str(e)}")
        isar_task: Task = Task(steps=[drive_step, *inspection_steps], tag_id=tag_id)
        isar_tasks.append(isar_task)

    if not isar_tasks:
        raise MissionPlannerError("Mission does not contain any valid tasks")

    isar_mission: Mission = Mission(tasks=isar_tasks)

    return isar_mission


def create_inspection_step(
    inspection_type: InspectionTypes,
    duration: float,
    target: Position,
    analysis: Optional[List],
    tag_id: Optional[str],
    metadata: Optional[dict],
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
    else:
        raise ValueError(f"Inspection type '{inspection_type}' not supported")

    if tag_id:
        inspection_step.tag_id = tag_id
    if analysis:
        inspection_step.analysis = analysis
    if metadata:
        inspection_step.metadata = metadata

    return inspection_step
