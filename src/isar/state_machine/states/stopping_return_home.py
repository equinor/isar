from typing import List

import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.returning_home as ReturningHome
from isar.apis.models.models import MissionStartResponse
from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.mission.mission import Mission


class StoppingReturnHome(State):

    def __init__(self, events: Events, mission: Mission):

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[EmptyMessage](
                name="failed_stop_event",
                event=events.robot_service_events.mission_failed_to_stop,
                handler=lambda _: ReturningHome.transition_to_existing_mission(),
            ),
            EventHandlerMapping[AbortedMission](
                name="successful_stop_event",
                event=events.robot_service_events.mission_successfully_stopped,
                handler=lambda event: Monitor.transition_and_start_mission(
                    mission, True
                ),
            ),
            EventHandlerMapping[EmptyMessage](
                name="mission_already_done_event",
                event=events.robot_service_events.stopped_mission_already_done,
                handler=lambda event: Monitor.transition_and_start_mission(
                    mission, True
                ),
            ),
        ]
        super().__init__(
            state_name=States.StoppingReturnHome,
            signal_exit_event=events.signal_state_machine_exit,
            event_handler_mappings=event_handlers,
        )


def transition_and_stop_return_home_and_reply_to_API(
    mission: Mission,
) -> Transition[StoppingReturnHome]:
    def _transition(events: Events) -> StoppingReturnHome:
        events.state_machine_events.stop_mission.trigger_event(EmptyMessage())
        response = MissionStartResponse(
            mission_id=mission.id,
            mission_started=True,
        )
        events.api_requests.start_mission.response.trigger_event(response)
        return StoppingReturnHome(events, mission)

    return _transition
