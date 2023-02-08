from typing import List, Optional, Union

from alitra import Frame, Orientation, Pose, Position
from pydantic import BaseModel, Field


class StepResponse(BaseModel):
    id: str
    type: str


class TaskResponse(BaseModel):
    id: str
    tag_id: Optional[str]
    steps: List[StepResponse]


class StartMissionResponse(BaseModel):
    id: str
    tasks: List[TaskResponse]


class ControlMissionResponse(BaseModel):
    mission_id: str
    mission_status: str
    task_id: str
    task_status: str
    step_id: str
    step_status: str


class RobotInfoResponse(BaseModel):
    robot_package: str
    isar_id: str
    robot_name: str
    robot_capabilities: List[str]
    robot_map_name: str
    plant_short_name: str


# We need to specify our own position/orientation/pose classes that do not contain
# the "Frame" class because of a bug in generating the OpenAPI specification:
# https://github.com/tiangolo/fastapi/issues/1505 This does not happen if all the
# classes are 'BaseModel' classes, but the alitra models are 'dataclasses', hence the
# conversion being done.
class InputOrientation(BaseModel):
    x: float
    y: float
    z: float
    w: float
    frame_name: str = Field(default="robot")

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
    frame_name: str = Field(default="robot")

    def to_alitra_position(self) -> Position:
        return Position(
            x=self.x,
            y=self.y,
            z=self.z,
            frame=Frame(self.frame_name),
        )


class InputPose(BaseModel):
    position: InputPosition
    orientation: InputOrientation
    frame_name: str = Field(default="robot")

    def to_alitra_pose(self) -> Pose:
        return Pose(
            position=self.position.to_alitra_position(),
            orientation=self.orientation.to_alitra_orientation(),
            frame=Frame(self.frame_name),
        )
