import isar.state_machine.states.return_home_paused as ReturnHomePaused
import isar.state_machine.states.returning_home as ReturningHome
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import EmptyMessage
from isar.state_machine.output_events import OutputEvent
from isar.state_machine.state import (
    Branch,
    EventHandler,
    StateDef,
    TransitionDef,
    TransitionEffect,
)
from isar.state_machine.states_enum import States

state: StateDef[None] = StateDef(
    name=States.ResumingReturnHome,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.action_requests.resume_mission.failure,
            branches=(Branch(ReturnHomePaused.transition),),
        ),
        EventHandler(
            event=lambda e: e.action_requests.resume_mission.success,
            branches=(Branch(ReturningHome.transition_with_existing_mission),),
        ),
    ),
)


transition_and_resume_return_home_and_respond_to_api: TransitionDef[None, None] = (
    TransitionDef(
        state,
        side_effects=(
            TransitionEffect(
                OutputEvent.api_response(lambda a: a.resume_mission),
                lambda _: ControlMissionResponse(success=True),
            ),
            TransitionEffect(
                OutputEvent.robot_request(lambda a: a.resume_mission),
                lambda _: EmptyMessage(),
            ),
        ),
    )
)
