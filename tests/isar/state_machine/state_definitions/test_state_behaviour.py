"""Per-state behaviour: given a state, an event and a message, which state follows and what is sent out."""

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import ANY

import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.going_to_lockdown as GoingToLockdown
import isar.state_machine.states.going_to_lockdown_with_mission as GoingToLockdownWithMission
import isar.state_machine.states.going_to_recharging as GoingToRecharging
import isar.state_machine.states.going_to_recharging_with_mission as GoingToRechargingWithMission
import isar.state_machine.states.home as Home
import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.lockdown as Lockdown
import isar.state_machine.states.lockdown_with_mission as LockdownWithMission
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.offline as Offline
import isar.state_machine.states.paused as Paused
import isar.state_machine.states.pausing as Pausing
import isar.state_machine.states.pausing_return_home as PausingReturnHome
import isar.state_machine.states.recharging as Recharging
import isar.state_machine.states.recharging_with_mission as RechargingWithMission
import isar.state_machine.states.resuming as Resuming
import isar.state_machine.states.resuming_return_home as ResumingReturnHome
import isar.state_machine.states.return_home_paused as ReturnHomePaused
import isar.state_machine.states.returning_home as ReturningHome
import isar.state_machine.states.stopping as Stopping
import isar.state_machine.states.stopping_due_to_maintenance as StoppingDueToMaintenance
import isar.state_machine.states.stopping_go_to_lockdown as StoppingGoToLockdown
import isar.state_machine.states.stopping_go_to_recharge as StoppingGoToRecharge
import isar.state_machine.states.stopping_paused_mission as StoppingPausedMission
import isar.state_machine.states.stopping_paused_return_home as StoppingPausedReturnHome
import isar.state_machine.states.stopping_return_home as StoppingReturnHome
import isar.state_machine.states.stopping_unknown_mission as StoppingUnknownMission
import isar.state_machine.states.unknown_status as UnknownStatus
from isar.apis.models.models import (
    LockdownResponse,
    MaintenanceResponse,
    MissionStartResponse,
)
from isar.config.settings import settings
from isar.models.events import EmptyMessage, Event, Events, MissionCompleted
from isar.state_machine.state import StateDef
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus, RobotStatus
from tests.isar.state_machine.state_definitions.state_machine_driver import (
    StateMachineDriver,
    state_machine_driver,
)

__all__ = ["state_machine_driver"]

MISSION = Mission(id="id", name="mission", tasks=[])
ERROR = ErrorMessage(
    error_reason=ErrorReason.RobotUnknownErrorException, error_description=""
)
EMPTY = EmptyMessage()
LOCKDOWN_STARTED = {"send_to_lockdown": LockdownResponse(lockdown_started=True)}
MAINTENANCE_STARTED = {
    "set_maintenance_mode": MaintenanceResponse(is_maintenance_mode=True)
}


def mission_status(status: MissionStatus) -> dict[str, Any]:
    return {"mission_id": "id", "status": status}


def intervention(reason: str) -> dict[str, Any]:
    return {"reason": reason}


_STATE_PARAM = object()


@dataclass(frozen=True)
class Expect:
    """The outcome of sending one message to a state."""

    message: Any
    state: States
    api: dict[str, Any] = field(default_factory=dict)
    robot: dict[str, Any] = field(default_factory=dict)
    mqtt: list[dict[str, Any]] = field(default_factory=list)
    param: Any = _STATE_PARAM  # overrides the parameter of the start state
    param_after: Any = field(default_factory=lambda: ANY)


@dataclass(frozen=True)
class StateCases:
    """Expectations for one state, keyed by the event that is sent.

    Events whose outcome depends on the message map to a dict of labelled expectations.
    """

    state: StateDef[Any]
    param: Any
    on: dict[Event[Any], Expect | dict[str, Expect]]


def state_cases(events: Events) -> list[StateCases]:
    return [
        StateCases(
            Monitor.state,
            "id",
            on={
                events.action_requests.execute_mission.success: Expect(
                    EMPTY,
                    States.AwaitNextMission,
                    mqtt=[mission_status(MissionStatus.Successful)],
                ),
                events.action_requests.execute_mission.failure: Expect(
                    ERROR,
                    States.AwaitNextMission,
                    mqtt=[mission_status(MissionStatus.Failed)],
                ),
                events.api_requests.stop_mission.request: Expect(
                    EMPTY,
                    States.Stopping,
                    api={"stop_mission": ANY},
                    robot={"stop_mission": ANY},
                ),
                events.api_requests.pause_mission.request: Expect(
                    EMPTY,
                    States.Pausing,
                    api={"pause_mission": ANY},
                    robot={"pause_mission": ANY},
                ),
                events.api_requests.send_to_lockdown.request: Expect(
                    EMPTY, States.StoppingGoToLockdown, robot={"stop_mission": ANY}
                ),
                events.robot_async_events.battery_below_mission_threshold: Expect(
                    EMPTY, States.StoppingGoToRecharge, robot={"stop_mission": ANY}
                ),
                events.api_requests.set_maintenance_mode.request: Expect(
                    EMPTY,
                    States.StoppingDueToMaintenance,
                    robot={"stop_mission": ANY},
                    param_after="id",
                ),
            },
        ),
        StateCases(
            Stopping.state,
            "id",
            on={
                events.action_requests.stop_mission.success: Expect(
                    EMPTY,
                    States.AwaitNextMission,
                    mqtt=[mission_status(MissionStatus.Cancelled)],
                ),
                events.action_requests.stop_mission.failure: Expect(
                    EMPTY, States.Monitor
                ),
            },
        ),
        StateCases(
            StoppingUnknownMission.state,
            None,
            on={
                events.action_requests.stop_mission.success: Expect(
                    EMPTY, States.AwaitNextMission
                ),
                events.action_requests.stop_mission.failure: Expect(
                    EMPTY,
                    States.InterventionNeeded,
                    mqtt=[intervention("Failed to stop unknown mission")],
                ),
            },
        ),
        StateCases(
            StoppingPausedMission.state,
            "id",
            on={
                events.action_requests.stop_mission.success: Expect(
                    EMPTY,
                    States.AwaitNextMission,
                    mqtt=[mission_status(MissionStatus.Cancelled)],
                ),
                events.action_requests.stop_mission.failure: Expect(
                    EMPTY, States.Paused, param_after="id"
                ),
            },
        ),
        StateCases(
            StoppingReturnHome.state,
            MISSION,
            on={
                events.action_requests.stop_mission.success: Expect(
                    EMPTY,
                    States.Monitor,
                    robot={"execute_mission": MISSION},
                    mqtt=[mission_status(MissionStatus.InProgress)],
                ),
                events.action_requests.stop_mission.failure: Expect(
                    EMPTY, States.ReturningHome
                ),
            },
        ),
        StateCases(
            StoppingPausedReturnHome.state,
            MISSION,
            on={
                events.action_requests.stop_mission.success: Expect(
                    EMPTY,
                    States.Monitor,
                    robot={"execute_mission": MISSION},
                    mqtt=[mission_status(MissionStatus.InProgress)],
                ),
                events.action_requests.stop_mission.failure: Expect(
                    EMPTY,
                    States.InterventionNeeded,
                    mqtt=[intervention("Failed to stop paused return home mission")],
                ),
            },
        ),
        StateCases(
            StoppingGoToRecharge.state,
            "id",
            on={
                events.action_requests.stop_mission.success: {
                    "mission completed": Expect(
                        MissionCompleted(MissionStatus.Successful),
                        States.GoingToRecharging,
                        robot={"return_home": ANY},
                        mqtt=[mission_status(MissionStatus.Successful)],
                    ),
                    "mission aborted": Expect(
                        MISSION,
                        States.GoingToRechargingWithMission,
                        robot={"return_home": ANY},
                        param_after=MISSION,
                    ),
                },
                events.action_requests.stop_mission.failure: Expect(
                    EMPTY,
                    States.InterventionNeeded,
                    mqtt=[intervention("Failed to stop mission when battery was low")],
                ),
            },
        ),
        StateCases(
            StoppingGoToLockdown.state,
            "id",
            on={
                events.action_requests.stop_mission.success: {
                    "mission aborted": Expect(
                        MISSION,
                        States.GoingToLockdownWithMission,
                        api=LOCKDOWN_STARTED,
                        robot={"return_home": ANY},
                    ),
                    "mission completed": Expect(
                        MissionCompleted(MissionStatus.Successful),
                        States.GoingToLockdown,
                        api=LOCKDOWN_STARTED,
                        robot={"return_home": ANY},
                        mqtt=[mission_status(MissionStatus.Successful)],
                    ),
                },
                events.action_requests.stop_mission.failure: Expect(
                    EMPTY,
                    States.Monitor,
                    api={
                        "send_to_lockdown": LockdownResponse(
                            lockdown_started=False,
                            failure_reason="Failed to stop ongoing mission",
                        )
                    },
                ),
            },
        ),
        StateCases(
            StoppingDueToMaintenance.state,
            "id",
            on={
                events.action_requests.stop_mission.success: {
                    "mission aborted": Expect(
                        MISSION,
                        States.Maintenance,
                        api=MAINTENANCE_STARTED,
                        mqtt=[
                            {
                                "mission_id": "id",
                                "reason": "Mission aborted, robot being sent to maintenance",
                            }
                        ],
                    ),
                    "mission completed": Expect(
                        MissionCompleted(MissionStatus.Successful),
                        States.Maintenance,
                        api=MAINTENANCE_STARTED,
                        mqtt=[mission_status(MissionStatus.Successful)],
                    ),
                },
                events.action_requests.stop_mission.failure: Expect(
                    EMPTY,
                    States.InterventionNeeded,
                    api={
                        "set_maintenance_mode": MaintenanceResponse(
                            is_maintenance_mode=False,
                            failure_reason="Failed to stop ongoing mission",
                        )
                    },
                    mqtt=[
                        intervention(
                            "Failed to stop mission when entering maintenance mode"
                        )
                    ],
                ),
            },
        ),
        StateCases(
            Maintenance.state,
            None,
            on={
                events.api_requests.release_from_maintenance_mode.request: Expect(
                    EMPTY,
                    States.UnknownStatus,
                    api={"release_from_maintenance_mode": ANY},
                ),
            },
        ),
        StateCases(
            GoingToLockdownWithMission.state,
            MISSION,
            on={
                events.action_requests.return_home.success: Expect(
                    EMPTY,
                    States.LockdownWithMission,
                    api=LOCKDOWN_STARTED,
                    param_after=MISSION,
                ),
                events.action_requests.return_home.failure: Expect(
                    ERROR,
                    States.InterventionNeeded,
                    mqtt=[
                        mission_status(MissionStatus.Failed),
                        intervention("Lockdown mission failed"),
                    ],
                ),
                events.action_requests.resume_mission.failure: Expect(
                    EMPTY,
                    States.InterventionNeeded,
                    mqtt=[
                        mission_status(MissionStatus.Failed),
                        intervention("Failed to resume return to home mission"),
                    ],
                ),
            },
        ),
        StateCases(
            GoingToRecharging.state,
            None,
            on={
                events.action_requests.return_home.success: Expect(
                    EMPTY, States.Recharging
                ),
                events.action_requests.return_home.failure: Expect(
                    ERROR,
                    States.InterventionNeeded,
                    mqtt=[intervention("Return home to recharge failed")],
                ),
                events.api_requests.send_to_lockdown.request: Expect(
                    EMPTY,
                    States.GoingToLockdown,
                    api={"send_to_lockdown": LockdownResponse(lockdown_started=True)},
                ),
            },
        ),
        StateCases(
            GoingToRechargingWithMission.state,
            MISSION,
            on={
                events.api_requests.stop_mission.request: Expect(
                    EMPTY, States.GoingToRecharging, api={"stop_mission": ANY}
                ),
                events.api_requests.send_to_lockdown.request: Expect(
                    EMPTY,
                    States.GoingToLockdownWithMission,
                    api=LOCKDOWN_STARTED,
                    param_after=MISSION,
                ),
                events.action_requests.return_home.success: Expect(
                    EMPTY, States.RechargingWithMission, param_after=MISSION
                ),
                events.action_requests.return_home.failure: Expect(
                    ERROR,
                    States.InterventionNeeded,
                    mqtt=[
                        mission_status(MissionStatus.Failed),
                        intervention("Return home to recharge failed"),
                    ],
                ),
            },
        ),
        StateCases(
            Recharging.state,
            None,
            on={
                events.robot_async_events.battery_above_recharge_threshold: Expect(
                    EMPTY, States.Home
                ),
                events.robot_async_events.robot_status_update: Expect(
                    RobotStatus.Offline, States.Offline
                ),
                events.api_requests.send_to_lockdown.request: Expect(
                    EMPTY, States.Lockdown, api=LOCKDOWN_STARTED
                ),
                events.api_requests.set_maintenance_mode.request: Expect(
                    EMPTY, States.Maintenance, api=MAINTENANCE_STARTED
                ),
            },
        ),
        StateCases(
            RechargingWithMission.state,
            MISSION,
            on={
                events.robot_async_events.battery_above_recharge_threshold: Expect(
                    EMPTY,
                    States.Monitor,
                    robot={"execute_mission": MISSION},
                    mqtt=[mission_status(MissionStatus.InProgress)],
                ),
                events.api_requests.stop_mission.request: Expect(
                    EMPTY, States.Recharging, api={"stop_mission": ANY}
                ),
                events.robot_async_events.robot_status_update: Expect(
                    RobotStatus.Offline, States.Offline
                ),
                events.api_requests.send_to_lockdown.request: Expect(
                    EMPTY, States.Lockdown, api=LOCKDOWN_STARTED
                ),
                events.api_requests.set_maintenance_mode.request: Expect(
                    EMPTY, States.Maintenance, api=MAINTENANCE_STARTED
                ),
            },
        ),
        StateCases(
            GoingToLockdown.state,
            None,
            on={
                events.action_requests.return_home.success: Expect(
                    EMPTY, States.Lockdown
                ),
                events.action_requests.return_home.failure: Expect(
                    ERROR,
                    States.InterventionNeeded,
                    mqtt=[intervention("Lockdown mission failed")],
                ),
                events.action_requests.resume_mission.failure: Expect(
                    EMPTY,
                    States.InterventionNeeded,
                    mqtt=[intervention("Failed to resume return to home mission")],
                ),
            },
        ),
        StateCases(
            Lockdown.state,
            None,
            on={
                events.api_requests.release_from_lockdown.request: Expect(
                    EMPTY, States.Home, api={"release_from_lockdown": ANY}
                ),
            },
        ),
        StateCases(
            LockdownWithMission.state,
            MISSION,
            on={
                events.api_requests.release_from_lockdown.request: Expect(
                    EMPTY,
                    States.Monitor,
                    api={"release_from_lockdown": ANY},
                    robot={"execute_mission": MISSION},
                    mqtt=[mission_status(MissionStatus.InProgress)],
                ),
            },
        ),
        StateCases(
            AwaitNextMission.state,
            None,
            on={
                events.api_requests.send_to_lockdown.request: Expect(
                    EMPTY,
                    States.GoingToLockdown,
                    api={"send_to_lockdown": LockdownResponse(lockdown_started=True)},
                    robot={"return_home": ANY},
                ),
                events.api_requests.start_mission.request: Expect(
                    MISSION,
                    States.Monitor,
                    api={"start_mission": MissionStartResponse(mission_started=True)},
                    robot={"execute_mission": MISSION},
                    mqtt=[mission_status(MissionStatus.InProgress)],
                    param_after="id",
                ),
                events.api_requests.return_home.request: Expect(
                    EMPTY,
                    States.ReturningHome,
                    api={"return_home": ANY},
                    robot={"return_home": ANY},
                ),
                events.api_requests.stop_mission.request: Expect(
                    EMPTY,
                    States.StoppingUnknownMission,
                    api={"stop_mission": ANY},
                    robot={"stop_mission": ANY},
                ),
                events.api_requests.set_maintenance_mode.request: Expect(
                    EMPTY, States.Maintenance, api=MAINTENANCE_STARTED
                ),
                events.robot_async_events.battery_below_mission_threshold: Expect(
                    EMPTY, States.GoingToRecharging, robot={"return_home": ANY}
                ),
            },
        ),
        StateCases(
            Home.state,
            None,
            on={
                events.robot_async_events.battery_below_mission_threshold: Expect(
                    EMPTY, States.Recharging
                ),
                events.robot_async_events.robot_status_update: {
                    "teleoperation": Expect(
                        RobotStatus.TeleOperation, States.Maintenance
                    ),
                    "still home": Expect(RobotStatus.Home, States.Home),
                    "available": Expect(RobotStatus.Available, States.AwaitNextMission),
                    "offline": Expect(RobotStatus.Offline, States.Offline),
                    "busy": Expect(RobotStatus.Busy, States.UnknownStatus),
                },
                events.api_requests.start_mission.request: Expect(
                    MISSION,
                    States.Monitor,
                    api={"start_mission": MissionStartResponse(mission_started=True)},
                    robot={"execute_mission": MISSION},
                    mqtt=[mission_status(MissionStatus.InProgress)],
                    param_after="id",
                ),
                events.api_requests.return_home.request: Expect(
                    EMPTY,
                    States.ReturningHome,
                    api={"return_home": ANY},
                    robot={"return_home": ANY},
                ),
                events.api_requests.stop_mission.request: Expect(
                    EMPTY,
                    States.StoppingUnknownMission,
                    api={"stop_mission": ANY},
                    robot={"stop_mission": ANY},
                ),
                events.api_requests.send_to_lockdown.request: Expect(
                    EMPTY, States.Lockdown, api=LOCKDOWN_STARTED
                ),
                events.api_requests.set_maintenance_mode.request: Expect(
                    EMPTY, States.Maintenance, api=MAINTENANCE_STARTED
                ),
            },
        ),
        StateCases(
            Paused.state,
            "id",
            on={
                events.api_requests.stop_mission.request: Expect(
                    EMPTY,
                    States.StoppingPausedMission,
                    api={"stop_mission": ANY},
                    robot={"stop_mission": ANY},
                ),
                events.api_requests.resume_mission.request: Expect(
                    EMPTY,
                    States.Resuming,
                    api={"resume_mission": ANY},
                    robot={"resume_mission": ANY},
                ),
                events.robot_async_events.battery_below_mission_threshold: Expect(
                    EMPTY, States.StoppingGoToRecharge, robot={"stop_mission": ANY}
                ),
                events.api_requests.send_to_lockdown.request: Expect(
                    EMPTY, States.StoppingGoToLockdown, robot={"stop_mission": ANY}
                ),
                events.api_requests.set_maintenance_mode.request: Expect(
                    EMPTY,
                    States.StoppingDueToMaintenance,
                    robot={"stop_mission": ANY},
                ),
            },
        ),
        StateCases(
            Pausing.state,
            "id",
            on={
                events.action_requests.pause_mission.success: Expect(
                    EMPTY, States.Paused, mqtt=[mission_status(MissionStatus.Paused)]
                ),
                events.action_requests.pause_mission.failure: Expect(
                    EMPTY, States.Monitor, param_after="id"
                ),
            },
        ),
        StateCases(
            Resuming.state,
            "id",
            on={
                events.action_requests.resume_mission.success: Expect(
                    EMPTY,
                    States.Monitor,
                    mqtt=[mission_status(MissionStatus.InProgress)],
                ),
                events.action_requests.resume_mission.failure: Expect(
                    EMPTY, States.Paused
                ),
            },
        ),
        StateCases(
            ReturningHome.state,
            0,
            on={
                events.action_requests.return_home.failure: {
                    "retries left": Expect(
                        ERROR,
                        States.ReturningHome,
                        robot={"return_home": ANY},
                        param=2,
                        param_after=1,
                    ),
                    "no retries left": Expect(
                        ERROR,
                        States.InterventionNeeded,
                        mqtt=[
                            intervention(
                                f"Return home failed after {settings.RETURN_HOME_RETRY_LIMIT} attempts"
                            )
                        ],
                    ),
                },
                events.api_requests.start_mission.request: Expect(
                    MISSION,
                    States.StoppingReturnHome,
                    api={
                        "start_mission": MissionStartResponse(
                            mission_id="id", mission_started=True
                        )
                    },
                    robot={"stop_mission": ANY},
                ),
                events.api_requests.pause_mission.request: Expect(
                    EMPTY,
                    States.PausingReturnHome,
                    api={"pause_mission": ANY},
                    robot={"pause_mission": ANY},
                ),
                events.api_requests.send_to_lockdown.request: Expect(
                    EMPTY,
                    States.GoingToLockdown,
                    api={"send_to_lockdown": LockdownResponse(lockdown_started=True)},
                ),
                events.robot_async_events.battery_below_mission_threshold: Expect(
                    EMPTY, States.GoingToRecharging
                ),
                events.action_requests.return_home.success: Expect(EMPTY, States.Home),
                events.api_requests.set_maintenance_mode.request: Expect(
                    EMPTY,
                    States.StoppingDueToMaintenance,
                    robot={"stop_mission": ANY},
                ),
            },
        ),
        StateCases(
            PausingReturnHome.state,
            None,
            on={
                events.action_requests.pause_mission.success: Expect(
                    EMPTY, States.ReturnHomePaused
                ),
                events.action_requests.pause_mission.failure: Expect(
                    EMPTY, States.ReturningHome
                ),
            },
        ),
        StateCases(
            ReturnHomePaused.state,
            None,
            on={
                events.api_requests.resume_mission.request: Expect(
                    EMPTY,
                    States.ResumingReturnHome,
                    api={"resume_mission": ANY},
                    robot={"resume_mission": ANY},
                ),
                events.api_requests.start_mission.request: Expect(
                    MISSION,
                    States.StoppingPausedReturnHome,
                    api={
                        "start_mission": MissionStartResponse(
                            mission_id="id", mission_started=True
                        )
                    },
                    robot={"stop_mission": ANY},
                ),
                events.api_requests.send_to_lockdown.request: Expect(
                    EMPTY,
                    States.GoingToLockdown,
                    api={"send_to_lockdown": ANY},
                    robot={"resume_mission": ANY},
                ),
                events.api_requests.set_maintenance_mode.request: Expect(
                    EMPTY,
                    States.StoppingDueToMaintenance,
                    robot={"stop_mission": ANY},
                ),
                events.robot_async_events.battery_below_mission_threshold: Expect(
                    EMPTY, States.ReturningHome
                ),
            },
        ),
        StateCases(
            ResumingReturnHome.state,
            None,
            on={
                events.action_requests.resume_mission.success: Expect(
                    EMPTY, States.ReturningHome
                ),
                events.action_requests.resume_mission.failure: Expect(
                    EMPTY, States.ReturnHomePaused
                ),
            },
        ),
        StateCases(
            UnknownStatus.state,
            None,
            on={
                events.robot_async_events.robot_status_update: {
                    "busy": Expect(
                        RobotStatus.Busy,
                        States.StoppingUnknownMission,
                        robot={"stop_mission": ANY},
                    ),
                    "available": Expect(RobotStatus.Available, States.AwaitNextMission),
                    "teleoperation": Expect(
                        RobotStatus.TeleOperation, States.Maintenance
                    ),
                    "home": Expect(RobotStatus.Home, States.Home),
                    "offline": Expect(RobotStatus.Offline, States.Offline),
                },
                events.api_requests.stop_mission.request: Expect(
                    EMPTY,
                    States.StoppingUnknownMission,
                    api={"stop_mission": ANY},
                    robot={"stop_mission": ANY},
                ),
                events.api_requests.set_maintenance_mode.request: Expect(
                    EMPTY, States.Maintenance, api=MAINTENANCE_STARTED
                ),
            },
        ),
        StateCases(
            Offline.state,
            None,
            on={
                events.robot_async_events.robot_status_update: {
                    "teleoperation": Expect(
                        RobotStatus.TeleOperation, States.Maintenance
                    ),
                    "home": Expect(RobotStatus.Home, States.Home),
                    "available": Expect(
                        RobotStatus.Available,
                        States.InterventionNeeded,
                        mqtt=[
                            intervention(
                                "Robot not home after going online. Localisation likely needed"
                            )
                        ],
                    ),
                    "busy": Expect(RobotStatus.Busy, States.UnknownStatus),
                },
                events.api_requests.set_maintenance_mode.request: Expect(
                    EMPTY, States.Maintenance, api=MAINTENANCE_STARTED
                ),
            },
        ),
        StateCases(
            InterventionNeeded.state,
            None,
            on={
                events.robot_async_events.robot_status_update: {
                    "home": Expect(RobotStatus.Home, States.Home),
                    "not home": Expect(
                        RobotStatus.Available, States.InterventionNeeded
                    ),
                },
                events.api_requests.release_intervention_needed.request: Expect(
                    EMPTY,
                    States.UnknownStatus,
                    api={"release_intervention_needed": ANY},
                ),
                events.api_requests.return_home.request: Expect(
                    EMPTY,
                    States.ReturningHome,
                    api={"return_home": ANY},
                    robot={"return_home": ANY},
                ),
                events.api_requests.set_maintenance_mode.request: Expect(
                    EMPTY, States.Maintenance, api=MAINTENANCE_STARTED
                ),
            },
        ),
    ]


@dataclass(frozen=True)
class Case:
    name: str
    start: StateDef[Any]
    param: Any
    event: Event[Any]
    expect: Expect


def all_cases(events: Events) -> Iterator[Case]:
    for cases in state_cases(events):
        for event, outcome in cases.on.items():
            labelled = outcome if isinstance(outcome, dict) else {"": outcome}
            for label, expect in labelled.items():
                param = cases.param if expect.param is _STATE_PARAM else expect.param
                name = f"{cases.state.name.value}: {event.name} {label}"
                yield Case(name, cases.state, param, event, expect)


def test_state_behaviour(
    events: Events, state_machine_driver: StateMachineDriver
) -> None:
    for case in all_cases(events):
        expect = case.expect
        state_machine_driver.enter(case.start, case.param)

        new_state = state_machine_driver.send(case.event, expect.message)
        outputs = state_machine_driver.outputs()

        assert new_state is expect.state, case.name
        assert state_machine_driver.state.param == expect.param_after, case.name
        assert outputs.api_responses == expect.api, case.name
        assert outputs.robot_requests == expect.robot, case.name
        assert len(outputs.mqtt) == len(expect.mqtt), case.name
        for payload, expected in zip(outputs.mqtt, expect.mqtt):
            assert expected.items() <= payload.items(), case.name


def test_await_next_mission_returns_home_after_delay(
    state_machine_driver: StateMachineDriver,
) -> None:
    state_machine_driver.enter(AwaitNextMission.state)

    assert (
        state_machine_driver.step(settings.RETURN_HOME_DELAY + 1)
        is States.ReturningHome
    )
    assert state_machine_driver.outputs().robot_requests == {"return_home": ANY}


def test_entering_home_discards_outdated_robot_status(
    state_machine_driver: StateMachineDriver,
) -> None:
    state_machine_driver.events.robot_async_events.robot_status_update.trigger_event(
        RobotStatus.Busy
    )
    state_machine_driver.enter(ReturningHome.state, 0)

    assert (
        state_machine_driver.send(
            state_machine_driver.events.action_requests.return_home.success, EMPTY
        )
        is States.Home
    )
    assert (
        not state_machine_driver.events.robot_async_events.robot_status_update.has_event()
    )
