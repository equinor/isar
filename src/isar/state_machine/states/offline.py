import isar.state_machine.states.home as Home
import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.unknown_status as UnknownStatus
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
    name=States.Offline,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.robot_async_events.robot_status_update,
            branches=(
                Branch(
                    Home.transition,
                    transition_when=lambda _, s: s == RobotStatus.Home,
                ),
                Branch(
                    InterventionNeeded.transition,
                    lambda _, __: "Robot not home after going online. Localisation likely needed",
                    transition_when=lambda _, s: s == RobotStatus.Available,
                ),
                Branch(
                    Maintenance.transition,
                    transition_when=lambda _, s: s == RobotStatus.TeleOperation,
                ),
                Branch(
                    UnknownStatus.transition,
                    transition_when=lambda _, s: s != RobotStatus.Offline,
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
