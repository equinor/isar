from enum import Enum


class MissionStatus(str, Enum):
    NotStarted = "not_started"
    InProgress = "in_progress"
    Paused = "paused"
    Failed = "failed"
    Cancelled = "cancelled"
    Successful = "successful"
    PartiallySuccessful = "partially_successful"


class TaskStatus(str, Enum):
    NotStarted = "not_started"
    InProgress = "in_progress"
    Paused = "paused"
    Failed = "failed"
    Cancelled = "cancelled"
    Successful = "successful"
    PartiallySuccessful = "partially_successful"


class RobotStatus(Enum):
    Available = "available"
    Busy = "busy"
    Home = "home"
    Offline = "offline"
    Blocked = "blocked"
    BlockedProtectiveStop = "blockedprotectivestop"
    ReturningHome = "returninghome"
