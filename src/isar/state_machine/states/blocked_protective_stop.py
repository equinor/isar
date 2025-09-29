from typing import TYPE_CHECKING, List

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.state_machine.utils.common_event_handlers import robot_status_event_handler
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class BlockedProtectiveStop(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events
        shared_state = state_machine.shared_state

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="robot_status_event",
                event=events.robot_service_events.robot_status_changed,
                handler=lambda event: robot_status_event_handler(
                    state_machine=state_machine,
                    expected_status=RobotStatus.BlockedProtectiveStop,
                    status_changed_event=event,
                    status_event=shared_state.robot_status,
                ),
            ),
        ]
        super().__init__(
            state_name="blocked_protective_stop",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
