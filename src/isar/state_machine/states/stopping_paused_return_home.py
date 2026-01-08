from typing import TYPE_CHECKING, List

import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.return_home_paused as ReturnHomePaused
from isar.apis.models.models import MissionStartResponse
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.models.events import EmptyMessage
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.mission import Mission

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class StoppingPausedReturnHome(State):

    def __init__(self, state_machine: "StateMachine", mission: Mission):
        events = state_machine.events

        response = MissionStartResponse(
            mission_id=mission.id,
            mission_started=True,
        )
        state_machine.events.api_requests.start_mission.response.trigger_event(response)

        def _failed_stop_return_home_event_handler(
            error_message: ErrorMessage,
        ) -> Transition[ReturnHomePaused.ReturnHomePaused]:
            state_machine.logger.warning(
                f"Failed to stop return home mission {error_message.error_description}"
            )
            return ReturnHomePaused.transition()

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[ErrorMessage](
                name="failed_stop_event",
                event=events.robot_service_events.mission_failed_to_stop,
                handler=_failed_stop_return_home_event_handler,
            ),
            EventHandlerMapping[EmptyMessage](
                name="successful_stop_event",
                event=events.robot_service_events.mission_successfully_stopped,
                handler=lambda event: Monitor.transition_and_start_mission(
                    mission, True
                ),
            ),
        ]
        super().__init__(
            state_name=States.StoppingPausedReturnHome,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition(mission: Mission) -> Transition[StoppingPausedReturnHome]:
    def _transition(state_machine: "StateMachine"):
        return StoppingPausedReturnHome(state_machine, mission)

    return _transition
