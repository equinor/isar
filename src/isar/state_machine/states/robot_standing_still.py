from typing import TYPE_CHECKING, List

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.state_machine.utils.generic_event_handlers import (
    check_and_handle_return_home_event,
    check_and_handle_robot_status_event,
    check_and_handle_start_mission_event,
    check_and_handle_stop_mission_event,
)
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def RobotStandingStill(state_machine: "StateMachine"):
    events = state_machine.events
    shared_state = state_machine.shared_state

    event_handlers: List[EventHandlerMapping] = [
        EventHandlerMapping(
            name="start_mission_event",
            eventQueue=events.api_requests.start_mission.input,
            handler=lambda event: check_and_handle_start_mission_event(
                state_machine, event
            ),
        ),
        EventHandlerMapping(
            name="return_home_event",
            eventQueue=events.api_requests.return_home.input,
            handler=lambda event: check_and_handle_return_home_event(
                state_machine, event
            ),
        ),
        EventHandlerMapping(
            name="stop_mission_event",
            eventQueue=events.api_requests.return_home.input,
            handler=lambda event: check_and_handle_stop_mission_event(
                state_machine, event
            ),
        ),
        EventHandlerMapping(
            name="robot_status_event",
            eventQueue=shared_state.robot_status,
            handler=lambda event: check_and_handle_robot_status_event(
                state_machine, RobotStatus.Available, event
            ),
        ),
    ]
    return EventHandlerBase(
        state_name="robot_standing_still",
        state_machine=state_machine,
        event_handler_mappings=event_handlers,
    )
