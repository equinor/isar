from enum import Enum


class States(str, Enum):
    Off = "off"
    Idle = "idle"
    Monitor = "monitor"
    Paused = "paused"
    Stop = "stop"
    Offline = "offline"
    BlockedProtectiveStop = "blocked_protective_stop"

    def __repr__(self):
        return self.value
