from enum import Enum


class States(str, Enum):
    Monitor = "monitor"
    ReturningHome = "returning_home"
    Stopping = "stopping"
    StoppingReturnHome = "stopping_return_home"
    Paused = "paused"
    Pausing = "pausing"
    Resuming = "resuming"
    PausingReturnHome = "pausing_return_home"
    ResumingReturnHome = "resuming_return_home"
    ReturnHomePaused = "return_home_paused"
    AwaitNextMission = "await_next_mission"
    Home = "home"
    Offline = "offline"
    UnknownStatus = "unknown_status"
    InterventionNeeded = "intervention_needed"
    Recharging = "recharging"
    RechargingWithMission = "recharging_with_mission"
    StoppingGoToLockdown = "stopping_go_to_lockdown"
    GoingToLockdown = "going_to_lockdown"
    Lockdown = "lockdown"
    GoingToRecharging = "going_to_recharging"
    GoingToRechargingWithMission = "going_to_recharging_with_mission"
    StoppingGoToRecharge = "stopping_go_to_recharge"
    Maintenance = "maintenance"
    StoppingDueToMaintenance = "stopping_due_to_maintenance"
    StoppingPausedMission = "stopping_paused_mission"
    StoppingPausedReturnHome = "stopping_paused_return_home"

    def __repr__(self) -> str:
        return self.value
