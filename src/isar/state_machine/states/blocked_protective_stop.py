from typing import TYPE_CHECKING, List

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class BlockedProtectiveStop(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        shared_state = state_machine.shared_state

        def _robot_status_event_handler(event: Event[RobotStatus]):
            robot_status: RobotStatus = event.check()
            if robot_status != RobotStatus.BlockedProtectiveStop:
                return state_machine.robot_status_changed  # type: ignore
            return None

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="robot_status_event",
                event=shared_state.robot_status,
                handler=_robot_status_event_handler,
            ),
        ]
        super().__init__(
            state_name="blocked_protective_stop",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
