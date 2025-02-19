from enum import Enum


class States(str, Enum):
    Off = "off"
    Docked = "docked"
    Idle = "idle"
    Monitor = "monitor"
    ReturningHome = "returning_home"
    AwaitNextMission = "await_next_mission"
    Paused = "paused"
    Stop = "stop"
    Offline = "offline"
    BlockedProtectiveStop = "blocked_protective_stop"
    UnknownStatus = "unknown_status"

    def __repr__(self):
        return self.value
