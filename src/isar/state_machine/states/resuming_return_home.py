import isar.state_machine.states.return_home_paused as ReturnHomePaused
import isar.state_machine.states.returning_home as ReturningHome
from isar.apis.models.models import ControlMissionResponse
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


def _respond_and_request_resume(events: OutputEvents, _: None) -> None:
    events.api.respond(lambda r: r.resume_mission, ControlMissionResponse(success=True))
    events.robot.request(lambda a: a.resume_mission, EmptyMessage())


transition_and_resume_return_home_and_respond_to_api: TransitionDef[None, None] = (
    TransitionDef(state, forward, side_effect=_respond_and_request_resume)
)
