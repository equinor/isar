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
    ReturnHomePaused = "returnhomepaused"
    Paused = "paused"
    Busy = "busy"
    Home = "home"
    Offline = "offline"
    BlockedProtectiveStop = "blockedprotectivestop"
    ReturningHome = "returninghome"
    InterventionNeeded = "interventionneeded"
    Recharging = "recharging"
    Lockdown = "lockdown"
    GoingToLockdown = "goingtolockdown"
