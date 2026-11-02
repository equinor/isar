import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.monitor as Monitor
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.state_machine.state import (
    EventHandlerMapping,
    StateDef,
    Transition,
    state_definition,
    transition_definition,
)
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.status import MissionStatus


@state_definition
def Stopping(events: Events, mission_id: str) -> StateDef:

    def _successful_stop_event_handler(
        _: AbortedMission | EmptyMessage,
    ) -> Transition:
        events.mqtt_queue.publish_mission_status(
            mission_id,
            MissionStatus.Cancelled,
            ErrorMessage(ErrorReason.RobotActionException, "Mission stopped by user"),
        )
        return AwaitNextMission.transition(events)

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.action_requests.stop_mission.failure,
            handler=lambda _: Monitor.transition_with_existing_mission(
                events, mission_id
            ),
        ),
        EventHandlerMapping[AbortedMission | EmptyMessage](
            event=events.action_requests.stop_mission.success,
            handler=_successful_stop_event_handler,
        ),
    ]
    return StateDef(
        name=States.Stopping,
        handlers=event_handlers,
    )


@transition_definition
def transition_and_trigger_stop_and_respond_to_API(
    events: Events,
    mission_id: str,
) -> Transition:
    def _side_effect(events: Events) -> None:
        events.action_requests.stop_mission.trigger_request(EmptyMessage())
        events.api_requests.stop_mission.trigger_response(
            ControlMissionResponse(success=True)
        )

    return Transition(Stopping(events, mission_id), _side_effect)
