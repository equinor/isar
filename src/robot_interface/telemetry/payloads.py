from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from alitra import Pose
from pydantic import BaseModel

from isar.models.status import IsarStatus
from isar.storage.storage_interface import BlobStoragePath
from robot_interface.models.exceptions.robot_exceptions import ErrorReason
from robot_interface.models.mission.status import MissionStatus, TaskStatus
from robot_interface.models.mission.task import TaskTypes
from robot_interface.models.robots.battery_state import BatteryState


class TelemetryPayload(BaseModel):
    isar_id: str
    robot_name: str
    timestamp: datetime


class CloudHealthPayload(BaseModel):
    isar_id: str
    robot_name: str
    timestamp: datetime


class TelemetryPosePayload(TelemetryPayload, BaseModel):
    pose: Pose


class TelemetryBatteryPayload(TelemetryPayload, BaseModel):
    battery_level: float
    battery_state: Optional[BatteryState] = None


class TelemetryObstacleStatusPayload(TelemetryPayload, BaseModel):
    obstacle_status: bool


class TelemetryPressurePayload(TelemetryPayload, BaseModel):
    pressure_level: float

class GenericFloatTelemetryPayload(TelemetryPayload, BaseModel):
    value: float
    name: str


@dataclass
class DocumentInfo:
    name: str
    url: str


class IsarStatusPayload(BaseModel):
    isar_id: str
    robot_name: str
    status: IsarStatus
    timestamp: datetime


class RobotInfoPayload(BaseModel):
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


class RobotHeartbeatPayload(BaseModel):
    isar_id: str
    robot_name: str
    timestamp: datetime


class MissionPayload(BaseModel):
    isar_id: str
    robot_name: str
    mission_id: Optional[str] = None
    status: Optional[MissionStatus] = None
    error_reason: Optional[ErrorReason] = None
    error_description: Optional[str] = None
    timestamp: datetime


class MissionAbortedPayload(BaseModel):
    isar_id: str
    robot_name: str
    mission_id: Optional[str] = None
    timestamp: datetime
    reason: Optional[str] = None


class TaskPayload(BaseModel):
    isar_id: str
    robot_name: str
    mission_id: Optional[str] = None
    task_id: Optional[str] = None
    status: Optional[TaskStatus] = None
    task_type: Optional[TaskTypes] = None
    error_reason: Optional[ErrorReason] = None
    error_description: Optional[str] = None
    timestamp: datetime


class InspectionResultPayload(BaseModel):
    isar_id: str
    robot_name: str
    inspection_id: str
    blob_storage_data_path: BlobStoragePath
    blob_storage_metadata_path: BlobStoragePath
    installation_code: str
    tag_id: Optional[str] = None
    inspection_type: Optional[str] = None
    inspection_description: Optional[str] = None
    timestamp: datetime


class InspectionValuePayload(BaseModel):
    isar_id: str
    robot_name: str
    inspection_id: str
    installation_code: str
    tag_id: Optional[str] = None
    inspection_type: Optional[str] = None
    inspection_description: Optional[str] = None
    value: float
    unit: str
    x: float
    y: float
    z: float
    timestamp: datetime


class StartUpMessagePayload(BaseModel):
    isar_id: str
    timestamp: datetime


class InterventionNeededPayload(BaseModel):
    isar_id: str
    robot_name: str
    reason: str
    timestamp: datetime
