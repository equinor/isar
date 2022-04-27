from .entity import Entity


class TelemetryPosePayload(Entity):
    class Pose(Entity):
        def __init__(
            self, x: float, y: float, z: float, yaw: float, pitch: float, roll: float
        ):
            self.x = x
            self.y = y
            self.z = z
            self.yaw = yaw
            self.pitch = pitch
            self.roll = roll

    def __init__(self, pose: Pose, timestamp: str):
        self.pose = pose
        self.timestamp = timestamp
