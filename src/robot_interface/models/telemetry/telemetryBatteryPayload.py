from .entity import Entity


class TelemetryBatteryPayload(Entity):
    def __init__(self, battery: float, timestamp: str):
        self.battery = battery
        self.timestamp = timestamp
