import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.lockdown as Lockdown
from isar.apis.models.models import LockdownResponse
from isar.models.events import EmptyMessage
from isar.state_machine.state import (
    Branch,
    EventHandler,
    StateDef,
    TransitionDef,
    TransitionEffect,
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


_respond: TransitionEffect[None] = TransitionEffect(
    lambda e: e.api_requests.send_to_lockdown.trigger_response,
    lambda _: LockdownResponse(lockdown_started=True),
)
_request_return_home: TransitionEffect[None] = TransitionEffect(
    lambda e: e.action_requests.return_home.trigger_request,
    lambda _: EmptyMessage(),
)

transition_with_existing_mission: TransitionDef[None, None] = TransitionDef(state)
transition_with_existing_mission_and_respond_to_api: TransitionDef[None, None] = (
    TransitionDef(state, effects=(_respond,))
)
transition_and_start_return_home_and_respond_to_api: TransitionDef[None, None] = (
    TransitionDef(state, effects=(_respond, _request_return_home))
)
