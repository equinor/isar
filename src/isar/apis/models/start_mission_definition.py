from pydantic import BaseModel, Field
from typing import List, Optional
from alitra import Pose, Position, Orientation, Frame
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


class InputOrientation(BaseModel):
    x: float
    y: float
    z: float
    w: float
    frame_name: str

    def to_alitra_orientation(self) -> Orientation:
        return Orientation(
            x=self.x,
            y=self.y,
            z=self.z,
            w=self.w,
            frame=Frame(self.frame_name),
        )


class InputPosition(BaseModel):
    x: float
    y: float
    z: float
    frame_name: str

    def to_alitra_position(self) -> Position:
        return Position(
            x=self.x,
            y=self.y,
            z=self.z,
            frame=Frame(self.frame_name),
        )


class InputPose(BaseModel):
    orientation: InputOrientation
    position: InputPosition
    frame_name: str

    def to_alitra_pose(self) -> Pose:
        return Pose(
            position=self.position.to_alitra_position(),
            orientation=self.orientation.to_alitra_orientation(),
            frame=Frame(self.frame_name),
        )


# We need to specify our own position/orientation/pose classes that do not contain the "Frame" class
# because of an bug in generating the OpenAPI specification:
# https://github.com/tiangolo/fastapi/issues/1505
# This does not happen if all the classes are 'BaseModel' classes, but the alitra models are 'dataclasses',
# hence the conversion being done.
class StartMissionTaskDefinition(BaseModel):
    pose: InputPose
    tag: Optional[str]
    inspection_target: InputPosition = Field(alias="InspectionTarget")
    sensors_types: List[str] = Field(alias="SensorTypes")
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
                    sensor_type=sensor,
                    duration=task.video_duration,
                    target=task.inspection_target,
                )
                for sensor in task.sensors_types
            ]
        except (ValueError) as e:
            raise MissionPlannerError(
                f"Failed to create task with exception message: '{str(e)}'"
            )
        isar_task: Task = Task(steps=[drive_step, *inspection_steps], tag_id=tag_id)
        isar_tasks.append(isar_task)

    if not isar_tasks:
        raise MissionPlannerError("Empty mission")

    isar_mission: Mission = Mission(tasks=isar_tasks)

    return isar_mission


def create_inspection_step(
    sensor_type: str, duration: float, target: Position
) -> STEPS:
    inspection: STEPS

    if sensor_type == TakeImage.type:
        inspection = TakeImage(target=target)
    elif sensor_type == TakeVideo.type:
        inspection = TakeVideo(target=target, duration=duration)
    elif sensor_type == TakeThermalImage.type:
        inspection = TakeThermalImage(target=target)
    elif sensor_type == TakeThermalVideo.type:
        inspection = TakeThermalVideo(target=target, duration=duration)
    else:
        raise ValueError(f"No step supported for sensor_type {sensor_type}")

    return inspection
