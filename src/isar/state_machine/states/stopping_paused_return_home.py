from typing import TYPE_CHECKING, List, Optional

from isar.apis.models.models import MissionStartResponse
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.state_machine.utils.common_event_handlers import (
    failed_stop_return_home_event_handler,
    successful_stop_return_home_event_handler,
)
from robot_interface.models.mission.mission import Mission

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class StoppingPausedReturnHome(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events
        self.mission: Optional[Mission] = None

        def _respond_to_start_mission_request():
            self.mission = (
                state_machine.events.api_requests.start_mission.request.consume_event()
            )
            if not self.mission:
                state_machine.logger.error(
                    "Reached stopping paused return home without a mission request"
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
                handler=lambda event: failed_stop_return_home_event_handler(
                    state_machine, event
                ),
            ),
            EventHandlerMapping(
                name="successful_stop_event",
                event=events.robot_service_events.mission_successfully_stopped,
                handler=lambda event: successful_stop_return_home_event_handler(
                    state_machine, event, self.mission
                ),
            ),
        ]
        super().__init__(
            state_name="stopping_paused_return_home",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
            on_entry=_respond_to_start_mission_request,
        )
