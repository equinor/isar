import isar.state_machine.states.home as Home
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.returning_home as ReturningHome
import isar.state_machine.states.unknown_status as UnknownStatus
from isar.models.events import EmptyMessage
from isar.state_machine.state import (
    Branch,
    EventHandler,
    HandlerEffect,
    StateDef,
    TransitionDef,
    TransitionEffect,
)
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import RobotStatus

state: StateDef[None] = StateDef(
    name=States.InterventionNeeded,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.api_requests.return_home.request,
            branches=(
                Branch(
                    ReturningHome.transition_and_return_home_and_respond_to_api,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.release_intervention_needed.request,
            branches=(
                Branch(
                    UnknownStatus.transition,
                    effects=(
                        HandlerEffect(
                            lambda e: e.api_requests.release_intervention_needed.trigger_response,
                            lambda _, __: EmptyMessage(),
                        ),
                    ),
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.set_maintenance_mode.request,
            branches=(Branch(Maintenance.transition_and_respond_to_api),),
        ),
        EventHandler(
            event=lambda e: e.robot_async_events.robot_status_update,
            branches=(
                Branch(
                    Home.transition,
                    transition_when=lambda _, s: s == RobotStatus.Home,
                ),
            ),
        ),
    ),
)


transition: TransitionDef[str, None] = TransitionDef(
    state,
    effects=(
        TransitionEffect(
            lambda e: e.mqtt_queue.publish_intervention_needed, lambda reason: reason
        ),
    ),
)
