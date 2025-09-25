from typing import TYPE_CHECKING, Callable, List, Optional

from isar.apis.models.models import LockdownResponse
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.status import MissionStatus, TaskStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class StoppingGoToLockdown(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

        def _stop_mission_cleanup() -> None:
            if state_machine.current_mission is None:
                state_machine._queue_empty_response()
                state_machine.reset_state_machine()
                return None

            state_machine.current_mission.status = MissionStatus.Cancelled

            for task in state_machine.current_mission.tasks:
                if task.status in [
                    TaskStatus.NotStarted,
                    TaskStatus.InProgress,
                    TaskStatus.Paused,
                ]:
                    task.status = TaskStatus.Cancelled

            state_machine.publish_task_status(task=state_machine.current_task)
            return None

        def _failed_stop_event_handler(
            event: Event[ErrorMessage],
        ) -> Optional[Callable]:
            error_message: Optional[ErrorMessage] = event.consume_event()
            if error_message is not None:
                events.api_requests.send_to_lockdown.response.trigger_event(
                    LockdownResponse(
                        lockdown_started=False,
                        failure_reason="Failed to stop ongoing mission",
                    )
                )
                return state_machine.mission_stopping_failed  # type: ignore
            return None

        def _successful_stop_event_handler(event: Event[bool]) -> Optional[Callable]:
            if event.consume_event():
                state_machine.publish_mission_aborted(
                    "Robot being sent to lockdown", True
                )
                _stop_mission_cleanup()
                events.api_requests.send_to_lockdown.response.trigger_event(
                    LockdownResponse(lockdown_started=True)
                )
                return state_machine.request_lockdown_mission  # type: ignore
            return None

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
            state_name="stopping_go_to_lockdown",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
