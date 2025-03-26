from enum import Enum


class States(str, Enum):
    Monitor = "monitor"
    ReturningHome = "returning_home"
    Stopping = "stopping"
    Paused = "paused"
    AwaitNextMission = "await_next_mission"
    Home = "home"
    RobotStandingStill = "robot_standing_still"
    Offline = "offline"
    BlockedProtectiveStop = "blocked_protective_stop"
    UnknownStatus = "unknown_status"

    def __repr__(self):
        return self.value
