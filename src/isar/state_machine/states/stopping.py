from typing import TYPE_CHECKING, Callable, List, Optional

from isar.apis.models.models import ControlMissionResponse
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.status import MissionStatus, TaskStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Stopping(EventHandlerBase):

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

            stopped_mission_response: ControlMissionResponse = (
                state_machine._make_control_mission_response()
            )
            state_machine.events.api_requests.stop_mission.response.trigger_event(
                stopped_mission_response
            )
            state_machine.publish_task_status(task=state_machine.current_task)
            state_machine._finalize()
            return None

        def _failed_stop_event_handler(
            event: Event[ErrorMessage],
        ) -> Optional[Callable]:
            error_message: Optional[ErrorMessage] = event.consume_event()
            if error_message is not None:
                return state_machine.mission_stopping_failed  # type: ignore
            return None

        def _successful_stop_event_handler(event: Event[bool]) -> Optional[Callable]:
            if event.consume_event():
                _stop_mission_cleanup()
                if not state_machine.battery_level_is_above_mission_start_threshold():
                    return state_machine.request_return_home  # type: ignore
                return state_machine.mission_stopped  # type: ignore
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
            state_name="stopping",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
