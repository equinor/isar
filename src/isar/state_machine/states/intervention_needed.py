import isar.state_machine.states.home as Home
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.returning_home as ReturningHome
import isar.state_machine.states.unknown_status as UnknownStatus
from isar.models.events import EmptyMessage
from isar.state_machine.capabilities import OutputEvents
from isar.state_machine.state import Branch, EventHandler, StateDef, TransitionDef
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import RobotStatus


def _accept_release(events: OutputEvents, _: None, __: EmptyMessage) -> None:
    events.api.respond(lambda r: r.release_intervention_needed, EmptyMessage())


state: StateDef[None] = StateDef(
    name=States.InterventionNeeded,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.api_requests.return_home.request,
            branches=(
                Branch(
                    ReturningHome.transition_and_return_home_and_respond_to_api,
                    ReturningHome.initial_retries,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.release_intervention_needed.request,
            branches=(Branch(UnknownStatus.transition, side_effect=_accept_release),),
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


def _publish_intervention_needed(events: OutputEvents, reason: str) -> None:
    events.mqtt.publish_intervention_needed(error_message=reason)


transition: TransitionDef[str, None] = TransitionDef(
    state, lambda _: None, side_effect=_publish_intervention_needed
)
