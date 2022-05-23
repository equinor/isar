from enum import Enum


class MissionStatus(str, Enum):
    NotStarted: str = "not_started"
    Started: str = "started"
    InProgress: str = "in_progress"
    Failed: str = "failed"
    Cancelled: str = "cancelled"
    Completed: str = "completed"
    Paused: str = "paused"


class TaskStatus(str, Enum):
    NotStarted: str = "not_started"
    InProgress: str = "in_progress"
    PartiallySuccessful: str = "partially_successful"
    Failed: str = "failed"
    Cancelled: str = "cancelled"
    Successful: str = "successful"
    Paused: str = "paused"
