from typing import List, Optional

from alitra import Position
from pydantic import BaseModel, Field

from isar.apis.models.models import InputPose, InputPosition
from isar.mission_planner.mission_planner_interface import MissionPlannerError
from isar.models.mission.mission import Mission, Task
from robot_interface.models.mission.step import (
    DriveToPose,
    InspectionStep,
    STEPS,
    TakeImage,
    TakeThermalImage,
    TakeThermalVideo,
    TakeVideo,
)

inspection_step_types: List[type[InspectionStep]] = [
    TakeImage,
    TakeThermalImage,
    TakeVideo,
    TakeThermalVideo,
]


class StartMissionTaskDefinition(BaseModel):
    pose: InputPose
    tag: Optional[str]
    inspection_target: InputPosition
    inspection_types: List[str] = Field(
        default=[step.get_inspection_type().__name__ for step in inspection_step_types]
    )
    video_duration: Optional[float] = Field(default=10)


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
                    inspection_type=inspection_type,
                    duration=task.video_duration,
                    target=task.inspection_target.to_alitra_position(),
                )
                for inspection_type in task.inspection_types
            ]
        except (ValueError) as e:
            raise MissionPlannerError(f"Failed to create task: {str(e)}")
        isar_task: Task = Task(steps=[drive_step, *inspection_steps], tag_id=tag_id)
        isar_tasks.append(isar_task)

    if not isar_tasks:
        raise MissionPlannerError("Mission does not contain any valid tasks")

    isar_mission: Mission = Mission(tasks=isar_tasks)

    return isar_mission


def create_inspection_step(
    inspection_type: str, duration: float, target: Position
) -> STEPS:
    inspection: STEPS

    if inspection_type == TakeImage.get_inspection_type().__name__:
        inspection = TakeImage(target=target)
    elif inspection_type == TakeVideo.get_inspection_type().__name__:
        inspection = TakeVideo(target=target, duration=duration)
    elif inspection_type == TakeThermalImage.get_inspection_type().__name__:
        inspection = TakeThermalImage(target=target)
    elif inspection_type == TakeThermalVideo.get_inspection_type().__name__:
        inspection = TakeThermalVideo(target=target, duration=duration)
    else:
        raise ValueError(f"Inspection type '{inspection_type}' not supported")

    return inspection
