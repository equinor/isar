from typing import TYPE_CHECKING, List

import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.paused as Paused
from isar.apis.models.models import ControlMissionResponse
from isar.eventhandlers.state import EventHandlerMapping, State, Transition
from isar.models.events import EmptyMessage
from isar.services.utilities.mqtt_utilities import publish_mission_status
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import MissionStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Pausing(State):

    def __init__(self, state_machine: "StateMachine", mission_id: str):
        events = state_machine.events

        def _successful_pause_event_handler(
            successful_pause: EmptyMessage,
        ) -> Transition[Paused.Paused]:
            publish_mission_status(
                state_machine.mqtt_publisher, mission_id, MissionStatus.Paused, None
            )
            return Paused.transition(mission_id)

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[EmptyMessage](
                name="failed_pause_event",
                event=events.robot_service_events.mission_failed_to_pause,
                handler=lambda _: Monitor.transition_with_existing_mission(mission_id),
            ),
            EventHandlerMapping[EmptyMessage](
                name="successful_pause_event",
                event=events.robot_service_events.mission_successfully_paused,
                handler=_successful_pause_event_handler,
            ),
        ]
        super().__init__(
            state_name=States.Pausing,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition_and_pause_mission_and_reply_to_API(
    mission_id: str,
) -> Transition[Pausing]:
    def _transition(state_machine: "StateMachine") -> Pausing:
        state_machine.events.api_requests.pause_mission.response.trigger_event(
            ControlMissionResponse(success=True)
        )
        state_machine.events.state_machine_events.pause_mission.trigger_event(
            EmptyMessage()
        )
        return Pausing(state_machine, mission_id=mission_id)

    return _transition
