from typing import TYPE_CHECKING, List

from isar.config.settings import settings
from isar.eventhandlers.eventhandler import (
    EventHandlerBase,
    EventHandlerMapping,
    TimeoutHandlerMapping,
)
from isar.state_machine.utils.generic_event_handlers import (
    check_and_handle_return_home_event,
    check_and_handle_start_mission_event,
    check_and_handle_stop_mission_event,
)

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def AwaitNextMission(state_machine: "StateMachine"):
    events = state_machine.events

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
    ]

    timers: List[TimeoutHandlerMapping] = [
        TimeoutHandlerMapping(
            name="should_return_home_timer",
            timeout_in_seconds=settings.RETURN_HOME_DELAY,
            handler=lambda: state_machine.request_return_home,  # type: ignore
        )
    ]

    return EventHandlerBase(
        state_name="await_next_mission",
        state_machine=state_machine,
        event_handler_mappings=event_handlers,
        timers=timers,
    )
