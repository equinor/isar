import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.monitor as Monitor
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.status import MissionStatus


def Stopping(events: Events, mission_id: str) -> State:

    def _successful_stop_event_handler(
        _: AbortedMission | EmptyMessage,
    ) -> Transition:
        events.mqtt_queue.publish_mission_status(
            mission_id,
            MissionStatus.Cancelled,
            ErrorMessage(ErrorReason.RobotActionException, "Mission stopped by user"),
        )
        return AwaitNextMission.transition()

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.robot_service_events.mission_failed_to_stop,
            handler=lambda _: Monitor.transition_with_existing_mission(mission_id),
        ),
        EventHandlerMapping[AbortedMission](
            event=events.robot_service_events.mission_successfully_stopped,
            handler=_successful_stop_event_handler,
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.robot_service_events.stopped_mission_already_done,
            handler=_successful_stop_event_handler,
        ),
    ]
    return State(
        state_name=States.Stopping,
        signal_exit_event=events.signal_state_machine_exit,
        event_handler_mappings=event_handlers,
    )


def transition_and_trigger_stop_and_respond_to_API(
    mission_id: str,
) -> Transition:
    def _transition(events: Events) -> State:
        events.state_machine_events.stop_mission.trigger_event(EmptyMessage())
        events.api_requests.stop_mission.response.trigger_event(
            ControlMissionResponse(success=True)
        )
        return Stopping(events, mission_id)

    return _transition
