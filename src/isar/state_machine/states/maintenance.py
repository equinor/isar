from typing import TYPE_CHECKING, List

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Maintenance(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

        def _release_from_maintenance_handler(event: Event[bool]):
            should_release_from_maintenance: bool = event.consume_event()
            if should_release_from_maintenance:
                events.api_requests.release_from_maintenance_mode.response.trigger_event(
                    True
                )
                return state_machine.release_from_maintenance  # type: ignore
            return None

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="release_from_maintenance",
                event=events.api_requests.release_from_maintenance_mode.request,
                handler=_release_from_maintenance_handler,
            ),
        ]

        super().__init__(
            state_name="maintenance",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
