from dataclasses import dataclass
from datetime import datetime
from typing import List

from alitra import Pose
from transitions import State

from robot_interface.models.mission.status import RobotStatus


@dataclass
class TelemetryPayload:
    isar_id: str
    robot_name: str
    timestamp: datetime


@dataclass
class TelemetryPosePayload(TelemetryPayload):
    pose: Pose


@dataclass
class TelemetryBatteryPayload(TelemetryPayload):
    battery_level: float


@dataclass
class TelemetryPressurePayload(TelemetryPayload):
    pressure_level: float


@dataclass
class VideoStream:
    name: str
    url: str
    type: str


@dataclass
class RobotStatusPayload:
    isar_id: str
    robot_name: str
    robot_status: RobotStatus
    current_isar_state: State
    current_mission_id: str
    current_task_id: str
    current_step_id: str
    timestamp: datetime


@dataclass
class RobotInfoPayload:
    isar_id: str
    robot_name: str
    robot_model: str
    robot_serial_number: str
    video_streams: List[VideoStream]
    host: str
    port: int
    timestamp: datetime
