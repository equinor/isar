from typing import TYPE_CHECKING, Callable, List, Optional

from isar.apis.models.models import ControlMissionResponse
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class ResumingReturnHome(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

        def _failed_resume_event_handler(
            event: Event[ErrorMessage],
        ) -> Optional[Callable]:
            error_message: Optional[ErrorMessage] = event.consume_event()

            if error_message is None:
                return None

            state_machine.events.api_requests.resume_mission.response.trigger_event(
                ControlMissionResponse(
                    success=False,
                    failure_reason=(
                        getattr(error_message, "error_reason", str(error_message))
                        if hasattr(error_message, "error_reason")
                        else str(error_message)
                    ),
                )
            )

            return state_machine.return_home_mission_resuming_failed  # type: ignore

        def _successful_resume_event_handler(event: Event[bool]) -> Optional[Callable]:
            if not event.consume_event():
                return None

            state_machine.events.api_requests.resume_mission.response.trigger_event(
                ControlMissionResponse(success=True)
            )

            return state_machine.return_home_mission_resumed  # type: ignore

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="failed_resume_event",
                event=events.robot_service_events.mission_failed_to_resume,
                handler=_failed_resume_event_handler,
            ),
            EventHandlerMapping(
                name="successful_resume_event",
                event=events.robot_service_events.mission_successfully_resumed,
                handler=_successful_resume_event_handler,
            ),
        ]
        super().__init__(
            state_name="resuming_return_home",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
