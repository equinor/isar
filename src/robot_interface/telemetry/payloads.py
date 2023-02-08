from dataclasses import dataclass
from datetime import datetime
from typing import List, Union
from uuid import UUID

from alitra import Pose
from transitions import State

from robot_interface.models.mission.status import RobotStatus


@dataclass
class TelemetryPosePayload:
    pose: Pose
    robot_id: str
    timestamp: datetime


@dataclass
class TelemetryBatteryPayload:
    battery_level: float
    robot_id: str
    timestamp: datetime


@dataclass
class VideoStream:
    name: str
    url: str
    type: str


@dataclass
class RobotStatusPayload:
    robot_name: str
    robot_status: RobotStatus
    current_isar_state: State
    current_mission_id: Union[UUID, int, str, None]
    current_task_id: UUID
    current_step_id: UUID
    timestamp: datetime


@dataclass
class RobotInfoPayload:
    robot_name: str
    robot_model: str
    robot_serial_number: str
    video_streams: List[VideoStream]
    host: str
    port: int
    timestamp: datetime
