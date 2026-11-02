import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.paused as Paused
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import (
    EventHandlerMapping,
    StateDef,
    Transition,
    state_definition,
    transition_definition,
)
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import MissionStatus


@state_definition
def Resuming(events: Events, mission_id: str) -> StateDef:

    def _successful_resume_event_handler(
        _: EmptyMessage,
    ) -> Transition:
        events.mqtt_queue.publish_mission_status(
            mission_id, MissionStatus.InProgress, None
        )
        return Monitor.transition_with_existing_mission(events, mission_id)

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.action_requests.resume_mission.failure,
            handler=lambda _: Paused.transition(events, mission_id),
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.action_requests.resume_mission.success,
            handler=_successful_resume_event_handler,
        ),
    ]
    return StateDef(
        name=States.Resuming,
        handlers=event_handlers,
    )


@transition_definition
def transition_resume_mission_and_respond_to_API(
    events: Events,
    mission_id: str,
) -> Transition:
    def _side_effect(events: Events) -> None:
        events.api_requests.resume_mission.trigger_response(
            ControlMissionResponse(success=True)
        )
        events.action_requests.resume_mission.trigger_request(EmptyMessage())

    return Transition(Resuming(events, mission_id), _side_effect)
