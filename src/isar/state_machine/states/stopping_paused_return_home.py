from typing import TYPE_CHECKING, List

import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.return_home_paused as ReturnHomePaused
from isar.apis.models.models import MissionStartResponse
from isar.models.events import AbortedMission, EmptyMessage
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.mission.mission import Mission

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class StoppingPausedReturnHome(State):

    def __init__(self, state_machine: "StateMachine", mission: Mission):
        events = state_machine.events

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[EmptyMessage](
                name="failed_stop_event",
                event=events.robot_service_events.mission_failed_to_stop,
                handler=lambda _: ReturnHomePaused.transition(),
            ),
            EventHandlerMapping[AbortedMission](
                name="successful_stop_event",
                event=events.robot_service_events.mission_successfully_stopped,
                handler=lambda _: Monitor.transition_and_start_mission(mission, True),
            ),
            EventHandlerMapping[EmptyMessage](
                name="mission_already_done_event",
                event=events.robot_service_events.stopped_mission_already_done,
                handler=lambda _: Monitor.transition_and_start_mission(mission, True),
            ),
        ]
        super().__init__(
            state_name=States.StoppingPausedReturnHome,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition_and_stop_return_home_and_reply_to_API(
    mission: Mission,
) -> Transition[StoppingPausedReturnHome]:
    def _transition(state_machine: "StateMachine") -> StoppingPausedReturnHome:
        state_machine.events.state_machine_events.stop_mission.trigger_event(
            EmptyMessage()
        )

        response = MissionStartResponse(
            mission_id=mission.id,
            mission_started=True,
        )
        state_machine.events.api_requests.start_mission.response.trigger_event(response)

        return StoppingPausedReturnHome(state_machine, mission)

    return _transition
