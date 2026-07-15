from typing import List

import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.paused as Paused
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.services.utilities.mqtt_utilities import publish_mission_status
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import MissionStatus


class StoppingPausedMission(State):

    def __init__(self, events: Events, mission_id: str):

        def _successful_stop_event_handler(
            successful_stop: AbortedMission | EmptyMessage,
        ) -> Transition[AwaitNextMission.AwaitNextMission]:
            publish_mission_status(
                events.mqtt_queue, mission_id, MissionStatus.Cancelled, None
            )
            return AwaitNextMission.transition()

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[EmptyMessage](
                name="failed_stop_event",
                event=events.robot_service_events.mission_failed_to_stop,
                handler=lambda _: Paused.transition(mission_id),
            ),
            EventHandlerMapping[AbortedMission](
                name="successful_stop_event",
                event=events.robot_service_events.mission_successfully_stopped,
                handler=_successful_stop_event_handler,
            ),
            EventHandlerMapping[EmptyMessage](
                name="mission_already_done_event",
                event=events.robot_service_events.stopped_mission_already_done,
                handler=_successful_stop_event_handler,
            ),
        ]
        super().__init__(
            state_name=States.StoppingPausedMission,
            signal_exit_event=events.signal_state_machine_exit,
            event_handler_mappings=event_handlers,
        )


def transition_and_trigger_stop(
    mission_id: str, should_respond_to_API_request: bool = False
) -> Transition[StoppingPausedMission]:
    def _transition(events: Events) -> StoppingPausedMission:
        events.state_machine_events.stop_mission.trigger_event(EmptyMessage())
        if should_respond_to_API_request:
            events.api_requests.stop_mission.response.trigger_event(
                ControlMissionResponse(success=True)
            )
        return StoppingPausedMission(events, mission_id)

    return _transition
