from enum import Enum

from .entity import Entity


class IsarStatePayload(Entity):
    class State(str, Enum):
        off = "off"
        idle = "idle"
        initiateStep = "initiate_step"
        monitor = "monitor"
        finalize = "finalize"

    def __init__(self, state: State, timestamp: str):
        self.state = state
        self.timestamp = timestamp
