from typing import List, Optional

from alitra import Frame, Orientation, Pose, Position
from pydantic import BaseModel, Field

from robot_interface.models.mission.task import TaskTypes


class TaskResponse(BaseModel):
    id: str
    tag_id: Optional[str] = None
    inspection_id: Optional[str] = None
    type: TaskTypes


class StartMissionResponse(BaseModel):
    id: str
    tasks: List[TaskResponse]


class ControlMissionResponse(BaseModel):
    mission_id: str
    mission_status: str
    task_id: str
    task_status: str


class RobotInfoResponse(BaseModel):
    robot_package: str
    isar_id: str
    robot_name: str
    robot_capabilities: List[str]
    robot_map_name: str
    plant_short_name: str


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
