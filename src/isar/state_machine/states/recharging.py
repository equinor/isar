import isar.state_machine.states.home as Home
import isar.state_machine.states.lockdown as Lockdown
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.offline as Offline
from isar.state_machine.state import (
    Branch,
    EventHandler,
    StateDef,
    TransitionDef,
    forward,
)
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import RobotStatus

state: StateDef[None] = StateDef(
    name=States.Recharging,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.robot_async_events.battery_above_recharge_threshold,
            branches=(Branch(Home.transition),),
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
    ),
)

transition: TransitionDef[None, None] = TransitionDef(state, forward)
