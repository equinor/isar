from enum import Enum


class States(str, Enum):

    Off = "off"
    Idle = "idle"
    Send = "send"
    Monitor = "monitor"
    Collect = "collect"
    Cancel = "cancel"

    def __repr__(self):
        return self.value
