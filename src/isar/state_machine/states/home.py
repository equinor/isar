from typing import TYPE_CHECKING, List

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.state_machine.utils.common_event_handlers import (
    return_home_event_handler,
    robot_status_event_handler,
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

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="start_mission_event",
                event=events.api_requests.start_mission.input,
                handler=lambda event: start_mission_event_handler(state_machine, event),
            ),
            EventHandlerMapping(
                name="return_home_event",
                event=events.api_requests.return_home.input,
                handler=lambda event: return_home_event_handler(state_machine, event),
            ),
            EventHandlerMapping(
                name="stop_mission_event",
                event=events.api_requests.return_home.input,
                handler=lambda event: stop_mission_event_handler(state_machine, event),
            ),
            EventHandlerMapping(
                name="robot_status_event",
                event=shared_state.robot_status,
                handler=lambda event: robot_status_event_handler(
                    state_machine, RobotStatus.Home, event
                ),
            ),
        ]
        super().__init__(
            state_name="home",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
