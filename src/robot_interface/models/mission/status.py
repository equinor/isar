from enum import Enum


class StepStatus(str, Enum):

    NotStarted: str = "not_started"
    Completed: str = "completed"
    PartiallySuccessful: str = "partially_successful"
    InProgress: str = "in_progress"
    Failed: str = "failed"
