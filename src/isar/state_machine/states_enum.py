from enum import Enum


class States(str, Enum):

    Off = "off"
    Idle = "idle"
    InitiateStep = "initiate_step"
    Monitor = "monitor"
    Finalize = "finalize"
    Paused = "paused"
    Stop = "stop"

    def __repr__(self):
        return self.value
