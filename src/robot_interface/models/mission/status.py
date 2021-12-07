from enum import Enum


class TaskStatus(str, Enum):

    NotStarted: str = "not_started"
    Completed: str = "completed"
    Scheduled: str = "scheduled"
    InProgress: str = "in_progress"
    Failed: str = "failed"
    Unexpected: str = "error_unexpected"
