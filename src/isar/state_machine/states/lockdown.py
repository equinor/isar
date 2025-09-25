from typing import TYPE_CHECKING, List

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Lockdown(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

        def _release_from_lockdown_handler(event: Event[bool]):
            should_release_from_lockdown: bool = event.consume_event()
            if should_release_from_lockdown:
                events.api_requests.release_from_lockdown.response.trigger_event(True)
                if state_machine.battery_level_is_above_mission_start_threshold():
                    return state_machine.release_from_lockdown  # type: ignore
                else:
                    return state_machine.starting_recharging  # type: ignore
            return None

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="release_from_lockdown",
                event=events.api_requests.release_from_lockdown.request,
                handler=_release_from_lockdown_handler,
            ),
        ]

        super().__init__(
            state_name="lockdown",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
