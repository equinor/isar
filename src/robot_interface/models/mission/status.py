from enum import Enum


class StepStatus(str, Enum):

    NotStarted: str = "not_started"
    Successful: str = "successful"
    InProgress: str = "in_progress"
    Failed: str = "failed"
    Cancelled: str = "cancelled"
