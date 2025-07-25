from typing import TYPE_CHECKING, List

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.communication.queues.events import Event
from isar.models.communication.queues.queue_utils import check_shared_state
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def BlockedProtectiveStop(state_machine: "StateMachine"):
    shared_state = state_machine.shared_state

    def _robot_status_event_handler(event: Event[RobotStatus]):
        robot_status: RobotStatus = check_shared_state(event)
        if robot_status != RobotStatus.BlockedProtectiveStop:
            return state_machine.robot_status_changed  # type: ignore
        return None

    event_handlers: List[EventHandlerMapping] = [
        EventHandlerMapping(
            name="robot_status_event",
            eventQueue=shared_state.robot_status,
            handler=_robot_status_event_handler,
        ),
    ]
    return EventHandlerBase(
        state_name="blocked_protective_stop",
        state_machine=state_machine,
        event_handler_mappings=event_handlers,
    )
