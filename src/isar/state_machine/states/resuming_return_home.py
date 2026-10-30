import isar.state_machine.states.return_home_paused as ReturnHomePaused
import isar.state_machine.states.returning_home as ReturningHome
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import (
    EventHandlerMapping,
    StateDef,
    Transition,
    state_definition,
)
from isar.state_machine.states_enum import States


@state_definition
def ResumingReturnHome(events: Events) -> StateDef:

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.action_requests.resume_mission.failure,
            handler=lambda _: ReturnHomePaused.transition(events),
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.action_requests.resume_mission.success,
            handler=lambda _: ReturningHome.transition_to_existing_mission(events),
        ),
    ]
    return StateDef(
        name=States.ResumingReturnHome,
        handlers=event_handlers,
    )


def transition_and_resume_mission_and_reply_to_API(events: Events) -> Transition:
    def _side_effect(events: Events) -> None:
        events.api_requests.resume_mission.trigger_response(
            ControlMissionResponse(success=True)
        )
        events.action_requests.resume_mission.trigger_request(EmptyMessage())

    return Transition(ResumingReturnHome(events), _side_effect)
