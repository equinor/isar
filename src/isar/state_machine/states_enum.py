from enum import Enum


class States(str, Enum):
    Monitor = "monitor"
    ReturningHome = "returning_home"
    Stopping = "stopping"
    StoppingReturnHome = "stopping_return_home"
    Paused = "paused"
    ReturnHomePaused = "return_home_paused"
    AwaitNextMission = "await_next_mission"
    Home = "home"
    Offline = "offline"
    BlockedProtectiveStop = "blocked_protective_stop"
    UnknownStatus = "unknown_status"
    InterventionNeeded = "intervention_needed"
    Recharging = "recharging"

    def __repr__(self):
        return self.value
