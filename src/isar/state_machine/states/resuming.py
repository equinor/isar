import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.paused as Paused
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import EmptyMessage, Events
from isar.services.utilities.mqtt_utilities import publish_mission_status
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import MissionStatus


def Resuming(events: Events, mission_id: str) -> State:

    def _successful_resume_event_handler(
        _: EmptyMessage,
    ) -> Transition:
        publish_mission_status(
            events.mqtt_queue, mission_id, MissionStatus.InProgress, None
        )
        return Monitor.transition_with_existing_mission(mission_id)

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.robot_service_events.mission_failed_to_resume,
            handler=lambda _: Paused.transition(mission_id),
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.robot_service_events.mission_successfully_resumed,
            handler=_successful_resume_event_handler,
        ),
    ]
    return State(
        state_name=States.Resuming,
        signal_exit_event=events.signal_state_machine_exit,
        event_handler_mappings=event_handlers,
    )


def transition_resume_mission_and_respond_to_API(
    mission_id: str,
) -> Transition:
    def _transition(events: Events) -> State:
        events.api_requests.resume_mission.response.trigger_event(
            ControlMissionResponse(success=True)
        )
        events.state_machine_events.resume_mission.trigger_event(EmptyMessage())
        return Resuming(events, mission_id)

    return _transition
