from typing import TYPE_CHECKING, Callable, List, Optional

from isar.apis.models.models import LockdownResponse
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.status import MissionStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class GoingToRecharging(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

        def _mission_failed_event_handler(
            event: Event[Optional[ErrorMessage]],
        ) -> Optional[Callable]:
            mission_failed: Optional[ErrorMessage] = event.consume_event()
            if mission_failed is None:
                return None

            state_machine.logger.warning(
                f"Failed to go to recharging because: "
                f"{mission_failed.error_description}"
            )
            state_machine.publish_intervention_needed(
                error_message="Return home to recharge failed."
            )
            state_machine.print_transitions()
            return state_machine.return_home_failed  # type: ignore

        def _mission_status_event_handler(
            event: Event[MissionStatus],
        ) -> Optional[Callable]:
            mission_status: Optional[MissionStatus] = event.consume_event()

            if not mission_status or mission_status in [
                MissionStatus.InProgress,
                MissionStatus.NotStarted,
                MissionStatus.Paused,
            ]:
                return None

            if mission_status != MissionStatus.Successful:
                state_machine.logger.warning(
                    "Failed to return home. Mission reported as failed."
                )
                state_machine.publish_intervention_needed(
                    error_message="Return home to recharge failed."
                )
                state_machine.print_transitions()
                return state_machine.return_home_failed  # type: ignore

            return state_machine.starting_recharging  # type: ignore

        def _send_to_lockdown_event_handler(
            event: Event[bool],
        ) -> Optional[Callable]:
            should_lockdown: bool = event.consume_event()
            if not should_lockdown:
                return None

            events.api_requests.send_to_lockdown.response.trigger_event(
                LockdownResponse(lockdown_started=True)
            )
            return state_machine.go_to_lockdown  # type: ignore

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="mission_failed_event",
                event=events.robot_service_events.mission_failed,
                handler=_mission_failed_event_handler,
            ),
            EventHandlerMapping(
                name="mission_status_event",
                event=events.robot_service_events.mission_status_updated,
                handler=_mission_status_event_handler,
            ),
            EventHandlerMapping(
                name="send_to_lockdown_event",
                event=events.api_requests.send_to_lockdown.request,
                handler=_send_to_lockdown_event_handler,
            ),
        ]
        super().__init__(
            state_name="going_to_recharging",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
