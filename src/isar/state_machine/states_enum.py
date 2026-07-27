from enum import Enum


class States(str, Enum):
    Monitor = "monitor"
    ReturningHome = "returning_home"
    Stopping = "stopping"
    StoppingUnknownMission = "stopping_unknown_mission"
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


STATE_TO_CODE: dict["States", int] = {
    States.Home: 0,
    States.AwaitNextMission: 1,
    States.Monitor: 2,
    States.ReturningHome: 3,
    States.Offline: 4,
    States.InterventionNeeded: 5,
    States.Maintenance: 6,
    States.Paused: 7,
    States.Pausing: 8,
    States.Resuming: 9,
    States.PausingReturnHome: 10,
    States.ResumingReturnHome: 11,
    States.ReturnHomePaused: 12,
    States.Stopping: 13,
    States.StoppingUnknownMission: 14,
    States.StoppingReturnHome: 15,
    States.StoppingPausedMission: 16,
    States.StoppingPausedReturnHome: 17,
    States.StoppingDueToMaintenance: 18,
    States.StoppingGoToLockdown: 19,
    States.StoppingGoToRecharge: 20,
    States.Recharging: 21,
    States.RechargingWithMission: 22,
    States.GoingToRecharging: 23,
    States.GoingToRechargingWithMission: 24,
    States.GoingToLockdown: 25,
    States.Lockdown: 26,
    States.UnknownStatus: 27,
}
