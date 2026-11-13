import isar.state_machine.states.lockdown as Lockdown
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.offline as Offline
import isar.state_machine.states.recharging as Recharging
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import AbortedMission, EmptyMessage
from isar.state_machine.capabilities import OutputEvents
from isar.state_machine.state import (
    Branch,
    EventHandler,
    StateDef,
    TransitionDef,
    forward,
    forward_state_parameter,
)
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import RobotStatus


def _accept_stop(events: OutputEvents, _: AbortedMission, __: EmptyMessage) -> None:
    events.api.respond(lambda r: r.stop_mission, ControlMissionResponse(success=True))


state: StateDef[AbortedMission] = StateDef(
    name=States.RechargingWithMission,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.robot_async_events.battery_above_recharge_threshold,
            branches=(
                Branch(Monitor.transition_and_start_mission, forward_state_parameter),
            ),
        ),
        EventHandler(
            event=lambda e: e.robot_async_events.robot_status_update,
            branches=(
                Branch(
                    Offline.transition,
                    transition_when=lambda _, s: s == RobotStatus.Offline,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.send_to_lockdown.request,
            branches=(Branch(Lockdown.transition_and_respond_to_api),),
        ),
        EventHandler(
            event=lambda e: e.api_requests.set_maintenance_mode.request,
            branches=(Branch(Maintenance.transition_and_respond_to_api),),
        ),
        EventHandler(
            event=lambda e: e.api_requests.stop_mission.request,
            branches=(Branch(Recharging.transition, side_effect=_accept_stop),),
        ),
    ),
)

transition: TransitionDef[AbortedMission, AbortedMission] = TransitionDef(
    state, forward
)
