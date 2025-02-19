from enum import Enum


class States(str, Enum):
    Off = "off"
    Docked = "docked"
    Idle = "idle"
    Initiate = "initiate"
    Initialize = "initialize"
    Monitor = "monitor"
    ReturningHome = "returning_home"
    AwaitNextMission = "await_next_mission"
    Paused = "paused"
    Stop = "stop"
    Offline = "offline"
    BlockedProtectiveStop = "blocked_protective_stop"

    def __repr__(self):
        return self.value
