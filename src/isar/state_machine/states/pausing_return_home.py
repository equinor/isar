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
def PausingReturnHome(events: Events) -> StateDef:

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.action_requests.pause_mission.failure,
            handler=lambda _: ReturningHome.transition_to_existing_mission(),
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.action_requests.pause_mission.success,
            handler=lambda _: ReturnHomePaused.transition(),
        ),
    ]
    return StateDef(
        name=States.PausingReturnHome,
        handlers=event_handlers,
    )


def transition_and_pause_mission_and_reply_to_API() -> Transition:
    def _transition(events: Events) -> StateDef:
        events.api_requests.pause_mission.trigger_response(
            ControlMissionResponse(success=True)
        )
        events.action_requests.pause_mission.trigger_request(EmptyMessage())
        return PausingReturnHome(events)

    return _transition
