import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.intervention_needed as InterventionNeeded
from isar.apis.models.models import ControlMissionResponse
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
    name=States.StoppingUnknownMission,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.action_requests.stop_mission.failure,
            branches=(
                Branch(
                    InterventionNeeded.transition,
                    lambda _, __: "Failed to stop unknown mission",
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.action_requests.stop_mission.success,
            branches=(Branch(AwaitNextMission.transition),),
        ),
    ),
)


_request_stop: TransitionEffect[None] = TransitionEffect(
    lambda e: e.action_requests.stop_mission.trigger_request,
    lambda _: EmptyMessage(),
)

transition_and_stop_mission: TransitionDef[None, None] = TransitionDef(
    state, effects=(_request_stop,)
)
transition_and_stop_mission_and_respond_to_api: TransitionDef[None, None] = (
    TransitionDef(
        state,
        effects=(
            _request_stop,
            TransitionEffect(
                lambda e: e.api_requests.stop_mission.trigger_response,
                lambda _: ControlMissionResponse(success=True),
            ),
        ),
    )
)
