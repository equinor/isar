import isar.state_machine.states.return_home_paused as ReturnHomePaused
import isar.state_machine.states.returning_home as ReturningHome
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
    name=States.PausingReturnHome,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.action_requests.pause_mission.failure,
            branches=(Branch(ReturningHome.transition_with_existing_mission),),
        ),
        EventHandler(
            event=lambda e: e.action_requests.pause_mission.success,
            branches=(Branch(ReturnHomePaused.transition),),
        ),
    ),
)


transition_and_pause_return_home_and_respond_to_api: TransitionDef[None, None] = (
    TransitionDef(
        state,
        effects=(
            TransitionEffect(
                lambda e: e.api_requests.pause_mission.trigger_response,
                lambda _: ControlMissionResponse(success=True),
            ),
            TransitionEffect(
                lambda e: e.action_requests.pause_mission.trigger_request,
                lambda _: EmptyMessage(),
            ),
        ),
    )
)
