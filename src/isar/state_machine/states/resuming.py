from typing import TYPE_CHECKING, List

import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.paused as Paused
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import EmptyMessage
from isar.services.utilities.mqtt_utilities import publish_mission_status
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import MissionStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Resuming(State):

    def __init__(self, state_machine: "StateMachine", mission_id: str):
        events = state_machine.events

        def _successful_resume_event_handler(
            successful_resume: EmptyMessage,
        ) -> Transition[Monitor.Monitor]:
            publish_mission_status(
                state_machine.mqtt_publisher, mission_id, MissionStatus.InProgress, None
            )
            return Monitor.transition_with_existing_mission(mission_id)

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[EmptyMessage](
                name="failed_resume_event",
                event=events.robot_service_events.mission_failed_to_resume,
                handler=lambda _: Paused.transition(mission_id),
            ),
            EventHandlerMapping[EmptyMessage](
                name="successful_resume_event",
                event=events.robot_service_events.mission_successfully_resumed,
                handler=_successful_resume_event_handler,
            ),
        ]
        super().__init__(
            state_name=States.Resuming,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition_resume_mission_and_respond_to_API(
    mission_id: str,
) -> Transition[Resuming]:
    def _transition(state_machine: "StateMachine") -> Resuming:
        state_machine.events.api_requests.resume_mission.response.trigger_event(
            ControlMissionResponse(success=True)
        )
        state_machine.events.state_machine_events.resume_mission.trigger_event(
            EmptyMessage()
        )
        return Resuming(state_machine, mission_id)

    return _transition
