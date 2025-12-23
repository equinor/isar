from typing import TYPE_CHECKING, List, Optional

from isar.apis.models.models import MissionStartResponse
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.models.events import Event
from isar.state_machine.states.return_home_paused import ReturnHomePaused
from isar.state_machine.states_enum import States
from isar.state_machine.utils.common_event_handlers import (
    successful_stop_return_home_event_handler,
)
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.mission import Mission

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class StoppingPausedReturnHome(State):

    @staticmethod
    def transition(mission: Mission) -> Transition["StoppingPausedReturnHome"]:
        def _transition(state_machine: "StateMachine"):
            return StoppingPausedReturnHome(state_machine, mission)

        return _transition

    def __init__(self, state_machine: "StateMachine", mission: Mission):
        events = state_machine.events

        response = MissionStartResponse(
            mission_id=mission.id,
            mission_started=True,
        )
        state_machine.events.api_requests.start_mission.response.trigger_event(response)

        def _failed_stop_return_home_event_handler(
            event: Event[ErrorMessage],
        ) -> Optional[Transition[ReturnHomePaused]]:
            error_message: Optional[ErrorMessage] = event.consume_event()
            if error_message is None:
                return None

            state_machine.logger.warning(
                f"Failed to stop return home mission {error_message.error_description}"
            )
            return ReturnHomePaused.transition()

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="failed_stop_event",
                event=events.robot_service_events.mission_failed_to_stop,
                handler=_failed_stop_return_home_event_handler,
            ),
            EventHandlerMapping(
                name="successful_stop_event",
                event=events.robot_service_events.mission_successfully_stopped,
                handler=lambda event: successful_stop_return_home_event_handler(
                    state_machine, event, mission
                ),
            ),
        ]
        super().__init__(
            state_name=States.StoppingPausedReturnHome,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
