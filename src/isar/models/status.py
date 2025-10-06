from enum import Enum


class IsarStatus(Enum):
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
