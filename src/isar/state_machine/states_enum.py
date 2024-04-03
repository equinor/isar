from enum import Enum


class States(str, Enum):
    Off = "off"
    Idle = "idle"
    Initiate = "initiate"
    Initialize = "initialize"
    Monitor = "monitor"
    Paused = "paused"
    Stop = "stop"
    Offline = "offline"

    def __repr__(self):
        return self.value
