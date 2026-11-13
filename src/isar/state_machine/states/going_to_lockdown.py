import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.lockdown as Lockdown
from isar.apis.models.models import LockdownResponse
from isar.models.events import EmptyMessage
from isar.state_machine.capabilities import OutputEvents
from isar.state_machine.state import (
    Branch,
    EventHandler,
    StateDef,
    TransitionDef,
    forward,
)
from isar.state_machine.states_enum import States

state: StateDef[None] = StateDef(
    name=States.GoingToLockdown,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.action_requests.return_home.failure,
            branches=(
                Branch(
                    InterventionNeeded.transition,
                    lambda _, __: "Lockdown mission failed",
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.action_requests.resume_mission.failure,
            branches=(
                Branch(
                    InterventionNeeded.transition,
                    lambda _, __: "Failed to resume return to home mission",
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.action_requests.return_home.success,
            branches=(Branch(Lockdown.transition),),
        ),
    ),
)


def _respond(events: OutputEvents, _: None) -> None:
    events.api.respond(
        lambda r: r.send_to_lockdown, LockdownResponse(lockdown_started=True)
    )


def _respond_and_request_return_home(events: OutputEvents, _: None) -> None:
    _respond(events, None)
    events.robot.request(lambda a: a.return_home, EmptyMessage())


transition_with_existing_mission: TransitionDef[None, None] = TransitionDef(
    state, forward
)
transition_with_existing_mission_and_respond_to_api: TransitionDef[None, None] = (
    TransitionDef(state, forward, side_effect=_respond)
)
transition_and_start_return_home_and_respond_to_api: TransitionDef[None, None] = (
    TransitionDef(state, forward, side_effect=_respond_and_request_return_home)
)
