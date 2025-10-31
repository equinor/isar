from typing import TYPE_CHECKING, Callable, List, Optional

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class BlockedProtectiveStop(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events
        shared_state = state_machine.shared_state

        def _robot_status_event_handler(
            status_changed_event: Event[bool],
        ) -> Optional[Callable]:
            has_changed = status_changed_event.consume_event()
            if not has_changed:
                return None
            robot_status: Optional[RobotStatus] = shared_state.robot_status.check()
            if robot_status == RobotStatus.BlockedProtectiveStop:
                return None
            elif robot_status == RobotStatus.Home:
                return state_machine.robot_status_home  # type: ignore
            elif robot_status == RobotStatus.Available:
                return state_machine.robot_status_available  # type: ignore
            elif robot_status == RobotStatus.Offline:
                return state_machine.robot_status_offline  # type: ignore
            return state_machine.robot_status_unknown  # type: ignore

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="robot_status_event",
                event=events.robot_service_events.robot_status_changed,
                handler=_robot_status_event_handler,
            ),
        ]
        super().__init__(
            state_name="blocked_protective_stop",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
