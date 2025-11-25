import logging
from typing import TYPE_CHECKING, Callable, List, Optional

from isar.apis.models.models import MissionStartResponse
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.mission import Mission

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class StoppingReturnHome(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        logger = logging.getLogger("state_machine")
        events = state_machine.events
        self.mission: Optional[Mission] = None

        def _failed_stop_event_handler(
            event: Event[ErrorMessage],
        ) -> Optional[Callable]:
            error_message: Optional[ErrorMessage] = event.consume_event()
            if error_message is None:
                return None

            logger.warning(error_message.error_description)
            mission: Mission = (
                state_machine.events.api_requests.start_mission.request.consume_event()
            )
            state_machine.events.api_requests.start_mission.response.trigger_event(
                MissionStartResponse(
                    mission_id=mission.id,
                    mission_started=False,
                    mission_not_started_reason="Failed to cancel return home mission",
                )
            )
            return state_machine.return_home_mission_stopping_failed  # type: ignore

        def _successful_stop_event_handler(event: Event[bool]) -> Optional[Callable]:
            if not event.consume_event():
                return None

            if self.mission:
                state_machine.start_mission(mission=self.mission)
                return state_machine.start_mission_monitoring  # type: ignore

            state_machine.logger.error(
                "Stopped return home without a new mission to start"
            )
            state_machine.start_return_home_mission()
            return state_machine.start_return_home_monitoring  # type: ignore

        def _respond_to_start_mission_request():
            self.mission = (
                state_machine.events.api_requests.start_mission.request.consume_event()
            )
            if not self.mission:
                state_machine.logger.error(
                    "Reached stopping return home without a mission request"
                )
            else:
                response = MissionStartResponse(
                    mission_id=self.mission.id,
                    mission_started=True,
                )
                state_machine.events.api_requests.start_mission.response.trigger_event(
                    response
                )

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="failed_stop_event",
                event=events.robot_service_events.mission_failed_to_stop,
                handler=_failed_stop_event_handler,
            ),
            EventHandlerMapping(
                name="successful_stop_event",
                event=events.robot_service_events.mission_successfully_stopped,
                handler=_successful_stop_event_handler,
            ),
        ]
        super().__init__(
            state_name="stopping_return_home",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
            on_entry=_respond_to_start_mission_request,
        )
