import isar.state_machine.states.monitor as Monitor
from isar.apis.models.models import LockdownResponse
from isar.models.events import AbortedMission, EmptyMessage
from isar.state_machine.state import (
    Branch,
    EventHandler,
    HandlerEffect,
    StateDef,
    TransitionDef,
    TransitionEffect,
    forward_state_parameter,
    forward_transition_parameter,
)
from isar.state_machine.states_enum import States

state: StateDef[AbortedMission] = StateDef(
    name=States.LockdownWithMission,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.api_requests.release_from_lockdown.request,
            branches=(
                Branch(
                    Monitor.transition_and_start_mission,
                    forward_state_parameter,
                    effects=(
                        HandlerEffect(
                            lambda e: e.api_requests.release_from_lockdown.trigger_response,
                            lambda _, __: EmptyMessage(),
                        ),
                    ),
                ),
            ),
        ),
    ),
)


transition_and_respond_to_api: TransitionDef[AbortedMission, AbortedMission] = (
    TransitionDef(
        state,
        forward_transition_parameter,
        effects=(
            TransitionEffect(
                lambda e: e.api_requests.send_to_lockdown.trigger_response,
                lambda _: LockdownResponse(lockdown_started=True),
            ),
        ),
    )
)
