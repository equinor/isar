from enum import Enum


class States(str, Enum):

    Off = "off"
    Idle = "idle"
    InitiateTask = "initiate_task"
    Monitor = "monitor"
    Finalize = "finalize"

    def __repr__(self):
        return self.value
