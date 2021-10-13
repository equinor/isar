from enum import Enum


class MissionStatus(str, Enum):

    Completed: str = "completed"
    Scheduled: str = "scheduled"
    InProgress: str = "in_progress"
    Failed: str = "failed"
    Unexpected: str = "error_unexpected"
