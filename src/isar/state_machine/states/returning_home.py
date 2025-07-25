from typing import TYPE_CHECKING, Callable, List, Optional

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.communication.message import StartMissionMessage
from isar.models.communication.queues.events import Event
from isar.models.communication.queues.queue_utils import (
    check_for_event_without_consumption,
)
from isar.state_machine.utils.generic_event_handlers import (
    mission_failed_event_handler,
    mission_started_event_handler,
    stop_mission_event_handler,
    task_status_event_handler,
    task_status_failed_event_handler,
)
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.status import TaskStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def ReturningHome(
    state_machine: "StateMachine",
) -> EventHandlerBase:
    events = state_machine.events

    def _handle_task_completed(status: TaskStatus):
        if status != TaskStatus.Successful:
            state_machine.current_mission.error_message = ErrorMessage(
                error_reason=ErrorReason.RobotActionException,
                error_description="Return home failed.",
            )
            return state_machine.return_home_failed  # type: ignore
        return state_machine.returned_home  # type: ignore

    def _start_mission_event_handler(
        event: Event[StartMissionMessage],
    ) -> Optional[Callable]:
        if check_for_event_without_consumption(event):
            return state_machine.stop  # type: ignore
        return None

    event_handlers: List[EventHandlerMapping] = [
        EventHandlerMapping(
            name="stop_mission_event",
            eventQueue=events.api_requests.stop_mission.input,
            # TODO: this will bring us to an inconsistent state. We don't yet have a frozen state.
            #       Ideally we should not allow stopping of a return home mission.
            handler=lambda event: stop_mission_event_handler(state_machine, event),
        ),
        EventHandlerMapping(
            name="mission_started_event",
            eventQueue=events.robot_service_events.mission_started,
            handler=lambda event: mission_started_event_handler(state_machine, event),
        ),
        EventHandlerMapping(
            name="mission_failed_event",
            eventQueue=events.robot_service_events.mission_failed,
            # TODO: this should lead us to retry going home, and if it keeps failing
            #       it should go to an error state
            handler=lambda event: mission_failed_event_handler(state_machine, event),
        ),
        EventHandlerMapping(
            name="start_mission_event",
            eventQueue=events.api_requests.start_mission.input,
            handler=_start_mission_event_handler,
        ),
        EventHandlerMapping(
            name="task_status_failed_event",
            eventQueue=events.robot_service_events.task_status_failed,
            handler=lambda event: task_status_failed_event_handler(
                state_machine, _handle_task_completed, event
            ),
        ),
        EventHandlerMapping(
            name="task_status_event",
            eventQueue=events.robot_service_events.task_status_updated,
            handler=lambda event: task_status_event_handler(
                state_machine, _handle_task_completed, event
            ),
        ),
    ]
    return EventHandlerBase(
        state_name="returning_home",
        state_machine=state_machine,
        event_handler_mappings=event_handlers,
    )
