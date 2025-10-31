from collections.abc import Callable
from typing import TYPE_CHECKING, List, Optional

from isar.apis.models.models import MaintenanceResponse
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from isar.state_machine.utils.common_event_handlers import return_home_event_handler

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class InterventionNeeded(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

        def _set_maintenance_mode_event_handler(event: Event[bool]):
            should_set_maintenande_mode: bool = event.consume_event()
            if should_set_maintenande_mode:
                events.api_requests.set_maintenance_mode.response.trigger_event(
                    MaintenanceResponse(is_maintenance_mode=True)
                )
                return state_machine.set_maintenance_mode  # type: ignore
            return None

        def release_intervention_needed_handler(
            event: Event[bool],
        ) -> Optional[Callable]:
            if not event.consume_event():
                return None

            state_machine.events.api_requests.release_intervention_needed.response.trigger_event(
                True
            )
            return state_machine.release_intervention_needed  # type: ignore

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
            EventHandlerMapping(
                name="set_maintenance_mode",
                event=events.api_requests.set_maintenance_mode.request,
                handler=_set_maintenance_mode_event_handler,
            ),
        ]
        super().__init__(
            state_name="intervention_needed",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
