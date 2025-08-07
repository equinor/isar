from typing import TYPE_CHECKING, Callable, List, Optional

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from isar.state_machine.utils.common_event_handlers import stop_mission_event_handler
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class UnknownStatus(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events
        shared_state = state_machine.shared_state

        def _robot_status_event_handler(
            event: Event[RobotStatus],
        ) -> Optional[Callable]:
            robot_status: RobotStatus = event.check()
            if (
                robot_status == RobotStatus.Home
                or robot_status == RobotStatus.Offline
                or robot_status == RobotStatus.BlockedProtectiveStop
                or robot_status == RobotStatus.Available
            ):
                return state_machine.robot_status_changed  # type: ignore
            return None

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="stop_mission_event",
                event=events.api_requests.stop_mission.request,
                handler=lambda event: stop_mission_event_handler(state_machine, event),
            ),
            EventHandlerMapping(
                name="robot_status_event",
                event=shared_state.robot_status,
                handler=_robot_status_event_handler,
            ),
        ]
        super().__init__(
            state_name="unknown_status",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
