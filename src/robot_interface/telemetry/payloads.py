from dataclasses import dataclass
from datetime import datetime

from alitra import Pose


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
