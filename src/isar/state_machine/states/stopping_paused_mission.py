import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.paused as Paused
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.state_machine.state import (
    EventHandlerMapping,
    StateDef,
    Transition,
    state_definition,
)
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import MissionStatus


@state_definition
def StoppingPausedMission(events: Events, mission_id: str) -> StateDef:

    def _successful_stop_event_handler(
        _: AbortedMission | EmptyMessage,
    ) -> Transition:
        events.mqtt_queue.publish_mission_status(
            mission_id, MissionStatus.Cancelled, None
        )
        return AwaitNextMission.transition()

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.action_requests.stop_mission.failure,
            handler=lambda _: Paused.transition(mission_id),
        ),
        EventHandlerMapping[AbortedMission | EmptyMessage](
            event=events.action_requests.stop_mission.success,
            handler=_successful_stop_event_handler,
        ),
    ]
    return StateDef(
        name=States.StoppingPausedMission,
        handlers=event_handlers,
    )


def transition_and_trigger_stop(
    mission_id: str, should_respond_to_API_request: bool = False
) -> Transition:
    def _transition(events: Events) -> StateDef:
        events.action_requests.stop_mission.trigger_request(EmptyMessage())
        if should_respond_to_API_request:
            events.api_requests.stop_mission.trigger_response(
                ControlMissionResponse(success=True)
            )
        return StoppingPausedMission(events, mission_id)

    return _transition
