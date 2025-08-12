from collections.abc import Callable
from typing import TYPE_CHECKING, List, Optional

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from isar.state_machine.utils.common_event_handlers import return_home_event_handler

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class InterventionNeeded(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

        def release_intervention_needed_handler(
            event: Event[bool],
        ) -> Optional[Callable]:
            if event.consume_event():
                state_machine.events.api_requests.release_intervention_needed.response.trigger_event(
                    True
                )
                return state_machine.release_intervention_needed  # type: ignore
            return None

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="return_home_event",
                event=events.api_requests.return_home.request,
                handler=lambda event: return_home_event_handler(state_machine, event),
            ),
            EventHandlerMapping(
                name="release_intervention_needed_event",
                event=events.api_requests.release_intervention_needed.request,
                handler=release_intervention_needed_handler,
            ),
        ]
        super().__init__(
            state_name="intervention_needed",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
