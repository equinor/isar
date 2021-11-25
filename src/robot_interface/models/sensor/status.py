from enum import Enum


class SensorStatus(Enum):
    Recording: str = "recording"
    Idle: str = "idle"
    NotAvailable: str = "not_available"
    Failed: str = "failed"
