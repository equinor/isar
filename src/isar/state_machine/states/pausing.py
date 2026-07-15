from typing import List

import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.paused as Paused
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import EmptyMessage, Events
from isar.services.utilities.mqtt_utilities import publish_mission_status
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import MissionStatus


class Pausing(State):

    def __init__(self, events: Events, mission_id: str):

        def _successful_pause_event_handler(
            successful_pause: EmptyMessage,
        ) -> Transition[Paused.Paused]:
            publish_mission_status(
                events.mqtt_queue, mission_id, MissionStatus.Paused, None
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
            signal_exit_event=events.signal_state_machine_exit,
            event_handler_mappings=event_handlers,
        )


def transition_and_pause_mission_and_reply_to_API(
    mission_id: str,
) -> Transition[Pausing]:
    def _transition(events: Events) -> Pausing:
        events.api_requests.pause_mission.response.trigger_event(
            ControlMissionResponse(success=True)
        )
        events.state_machine_events.pause_mission.trigger_event(EmptyMessage())
        return Pausing(events, mission_id=mission_id)

    return _transition
