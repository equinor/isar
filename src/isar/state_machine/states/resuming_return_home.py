from typing import List

import isar.state_machine.states.return_home_paused as ReturnHomePaused
import isar.state_machine.states.returning_home as ReturningHome
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States


class ResumingReturnHome(State):

    def __init__(self, events: Events):

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[EmptyMessage](
                name="failed_resume_event",
                event=events.robot_service_events.mission_failed_to_resume,
                handler=lambda _: ReturnHomePaused.transition(),
            ),
            EventHandlerMapping[EmptyMessage](
                name="successful_resume_event",
                event=events.robot_service_events.mission_successfully_resumed,
                handler=lambda _: ReturningHome.transition_to_existing_mission(),
            ),
        ]
        super().__init__(
            state_name=States.ResumingReturnHome,
            signal_exit_event=events.signal_state_machine_exit,
            event_handler_mappings=event_handlers,
        )


def transition_and_resume_mission_and_reply_to_API() -> Transition[ResumingReturnHome]:
    def _transition(events: Events) -> ResumingReturnHome:
        events.api_requests.resume_mission.response.trigger_event(
            ControlMissionResponse(success=True)
        )
        events.state_machine_events.resume_mission.trigger_event(EmptyMessage())
        return ResumingReturnHome(events)

    return _transition
