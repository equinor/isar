from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Union

from alitra import Pose

from robot_interface.models.exceptions.robot_exceptions import ErrorReason
from robot_interface.models.mission.status import MissionStatus, RobotStatus, TaskStatus
from robot_interface.models.mission.task import TaskTypes
from robot_interface.models.robots.battery_state import BatteryState


@dataclass
class TelemetryPayload:
    isar_id: str
    robot_name: str
    timestamp: datetime


@dataclass
class CloudHealthPayload:
    isar_id: str
    robot_name: str
    timestamp: datetime


@dataclass
class TelemetryPosePayload(TelemetryPayload):
    pose: Pose


@dataclass
class TelemetryBatteryPayload(TelemetryPayload):
    battery_level: float
    battery_state: Optional[BatteryState] = None


@dataclass
class TelemetryObstacleStatusPayload(TelemetryPayload):
    obstacle_status: bool


@dataclass
class TelemetryPressurePayload(TelemetryPayload):
    pressure_level: float


@dataclass
class DocumentInfo:
    name: str
    url: str


@dataclass
class RobotStatusPayload:
    isar_id: str
    robot_name: str
    status: RobotStatus
    timestamp: datetime


@dataclass
class RobotInfoPayload:
    isar_id: str
    robot_name: str
    robot_model: str
    robot_serial_number: str
    robot_asset: str
    documentation: List[DocumentInfo]
    host: str
    port: int
    capabilities: List[str]
    timestamp: datetime


@dataclass
class RobotHeartbeatPayload:
    isar_id: str
    robot_name: str
    timestamp: datetime


@dataclass
class MissionPayload:
    isar_id: str
    robot_name: str
    mission_id: Optional[str]
    status: Optional[MissionStatus]
    error_reason: Optional[ErrorReason]
    error_description: Optional[str]
    timestamp: datetime


@dataclass
class TaskPayload:
    isar_id: str
    robot_name: str
    mission_id: Optional[str]
    task_id: Optional[str]
    status: Optional[TaskStatus]
    task_type: Optional[TaskTypes]
    error_reason: Optional[ErrorReason]
    error_description: Optional[str]
    timestamp: datetime


@dataclass
class InspectionResultPayload:
    isar_id: str
    robot_name: str
    inspection_id: str
    inspection_path: Union[str, dict]
    installation_code: str
    tag_id: Optional[str]
    inspection_type: Optional[str]
    inspection_description: Optional[str]
    timestamp: datetime
