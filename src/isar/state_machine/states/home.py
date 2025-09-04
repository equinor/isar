from typing import TYPE_CHECKING, Callable, List, Optional

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from isar.state_machine.utils.common_event_handlers import (
    return_home_event_handler,
    start_mission_event_handler,
    stop_mission_event_handler,
)
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Home(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events
        shared_state = state_machine.shared_state

        def _robot_status_event_handler(
            event: Event[RobotStatus],
        ) -> Optional[Callable]:
            robot_status: RobotStatus = event.check()
            if not (
                robot_status == RobotStatus.Available
                or robot_status == RobotStatus.Home
            ):
                return state_machine.robot_status_changed  # type: ignore
            return None

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="start_mission_event",
                event=events.api_requests.start_mission.request,
                handler=lambda event: start_mission_event_handler(
                    state_machine, event, events.api_requests.start_mission.response
                ),
            ),
            EventHandlerMapping(
                name="return_home_event",
                event=events.api_requests.return_home.request,
                handler=lambda event: return_home_event_handler(state_machine, event),
            ),
            EventHandlerMapping(
                name="stop_mission_event",
                event=events.api_requests.return_home.request,
                handler=lambda event: stop_mission_event_handler(state_machine, event),
            ),
            EventHandlerMapping(
                name="robot_status_event",
                event=shared_state.robot_status,
                handler=_robot_status_event_handler,
            ),
        ]
        super().__init__(
            state_name="home",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
