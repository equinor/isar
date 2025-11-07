from typing import TYPE_CHECKING, Callable, List, Optional

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from isar.state_machine.utils.common_event_handlers import mission_started_event_handler
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.status import MissionStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class GoingToLockdown(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

        def _mission_failed_event_handler(
            event: Event[Optional[ErrorMessage]],
        ) -> Optional[Callable]:
            mission_failed: Optional[ErrorMessage] = event.consume_event()
            if mission_failed is None:
                return None

            state_machine.logger.warning(
                f"Failed to go to lockdown because: "
                f"{mission_failed.error_description}"
            )
            return state_machine.lockdown_mission_failed  # type: ignore

        def _mission_failed_to_resume_event_handler(
            event: Event[Optional[ErrorMessage]],
        ) -> Optional[Callable]:
            mission_failed_to_resume: Optional[ErrorMessage] = event.consume_event()
            if mission_failed_to_resume is None:
                return None

            state_machine.logger.warning(
                f"Failed to resume return to home mission and going to lockdown because: "
                f"{mission_failed_to_resume.error_description or ''}"
            )
            return state_machine.lockdown_mission_failed  # type: ignore

        def _mission_status_event_handler(
            event: Event[MissionStatus],
        ) -> Optional[Callable]:
            mission_status: Optional[MissionStatus] = event.consume_event()

            if mission_status and mission_status not in [
                MissionStatus.InProgress,
                MissionStatus.NotStarted,
                MissionStatus.Paused,
            ]:
                if mission_status != MissionStatus.Successful:
                    return state_machine.lockdown_mission_failed  # type: ignore

                return state_machine.reached_lockdown  # type: ignore
            return None

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="mission_started_event",
                event=events.robot_service_events.mission_started,
                handler=lambda event: mission_started_event_handler(
                    state_machine, event
                ),
            ),
            EventHandlerMapping(
                name="mission_failed_event",
                event=events.robot_service_events.mission_failed,
                handler=_mission_failed_event_handler,
            ),
            EventHandlerMapping(
                name="mission_failed_to_resume",
                event=events.robot_service_events.mission_failed_to_resume,
                handler=_mission_failed_to_resume_event_handler,
            ),
            EventHandlerMapping(
                name="mission_status_event",
                event=events.robot_service_events.mission_status_updated,
                handler=_mission_status_event_handler,
            ),
        ]
        super().__init__(
            state_name="going_to_lockdown",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
