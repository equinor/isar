from enum import Enum


class IsarStatus(Enum):
    Available = "available"
    ReturnHomePaused = "returnhomepaused"
    Paused = "paused"
    Busy = "busy"
    Home = "home"
    Offline = "offline"
    ReturningHome = "returninghome"
    InterventionNeeded = "interventionneeded"
    Recharging = "recharging"
    RechargingWithMission = "rechargingwithmission"
    Lockdown = "lockdown"
    GoingToLockdown = "goingtolockdown"
    GoingToRecharging = "goingtorecharging"
    GoingToRechargingWithMission = "goingtorechargingwithmission"
    Maintenance = "maintenance"
    Pausing = "pausing"
    PausingReturnHome = "pausingreturnhome"
    Stopping = "stopping"
    StoppingReturnHome = "stoppingreturnhome"
