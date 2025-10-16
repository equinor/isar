from typing import TYPE_CHECKING, Callable, List, Optional

from isar.apis.models.models import ControlMissionResponse
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.status import MissionStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Pausing(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

        def _failed_pause_event_handler(
            event: Event[ErrorMessage],
        ) -> Optional[Callable]:
            error_message: Optional[ErrorMessage] = event.consume_event()

            state_machine.events.api_requests.pause_mission.response.trigger_event(
                ControlMissionResponse(
                    success=False, failure_reason="Failed to pause mission in ISAR"
                )
            )

            state_machine.publish_mission_status()

            if error_message is None:
                return None

            return state_machine.mission_pausing_failed  # type: ignore

        def _successful_pause_event_handler(event: Event[bool]) -> Optional[Callable]:
            if not event.consume_event():
                return None

            state_machine.current_mission.status = MissionStatus.Paused

            state_machine.events.api_requests.pause_mission.response.trigger_event(
                ControlMissionResponse(success=True)
            )

            state_machine.publish_mission_status()

            return state_machine.mission_paused  # type:ignore

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="failed_pause_event",
                event=events.robot_service_events.mission_failed_to_pause,
                handler=_failed_pause_event_handler,
            ),
            EventHandlerMapping(
                name="successful_pause_event",
                event=events.robot_service_events.mission_successfully_paused,
                handler=_successful_pause_event_handler,
            ),
        ]
        super().__init__(
            state_name="pausing",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
