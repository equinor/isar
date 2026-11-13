import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.home as Home
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.offline as Offline
import isar.state_machine.states.stopping_unknown_mission as StoppingUnknownMission
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
    name=States.UnknownStatus,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.api_requests.stop_mission.request,
            branches=(
                Branch(
                    StoppingUnknownMission.transition_and_stop_mission_and_respond_to_api
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.robot_async_events.robot_status_update,
            branches=(
                Branch(
                    Home.transition,
                    transition_when=lambda _, s: s == RobotStatus.Home,
                ),
                Branch(
                    AwaitNextMission.transition,
                    transition_when=lambda _, s: s == RobotStatus.Available,
                ),
                Branch(
                    Offline.transition,
                    transition_when=lambda _, s: s == RobotStatus.Offline,
                ),
                Branch(
                    Maintenance.transition,
                    transition_when=lambda _, s: s == RobotStatus.TeleOperation,
                ),
                Branch(
                    StoppingUnknownMission.transition_and_stop_mission,
                    transition_when=lambda _, s: s == RobotStatus.Busy,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.set_maintenance_mode.request,
            branches=(Branch(Maintenance.transition_and_respond_to_api),),
        ),
    ),
)

transition: TransitionDef[None, None] = TransitionDef(state, forward)
