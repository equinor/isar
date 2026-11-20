import isar.state_machine.states.going_to_lockdown as GoingToLockdown
import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.recharging as Recharging
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
    name=States.GoingToRecharging,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.action_requests.return_home.failure,
            branches=(
                Branch(
                    InterventionNeeded.transition,
                    lambda _, __: "Return home to recharge failed",
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.action_requests.return_home.success,
            branches=(Branch(Recharging.transition),),
        ),
        EventHandler(
            event=lambda e: e.api_requests.send_to_lockdown.request,
            branches=(
                Branch(
                    GoingToLockdown.transition_with_existing_mission_and_respond_to_api
                ),
            ),
        ),
    ),
)


transition_with_existing_return_home: TransitionDef[None, None] = TransitionDef(state)
transition_and_start_return_home: TransitionDef[None, None] = TransitionDef(
    state,
    effects=(
        TransitionEffect(
            lambda e: e.action_requests.return_home.trigger_request,
            lambda _: EmptyMessage(),
        ),
    ),
)
