from typing import TYPE_CHECKING, List

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.state_machine.utils.common_event_handlers import (
    failed_stop_event_handler,
    successful_stop_event_handler,
)

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class StoppingPausedMission(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="failed_stop_event",
                event=events.robot_service_events.mission_failed_to_stop,
                handler=lambda event: failed_stop_event_handler(state_machine, event),
            ),
            EventHandlerMapping(
                name="successful_stop_event",
                event=events.robot_service_events.mission_successfully_stopped,
                handler=lambda event: successful_stop_event_handler(
                    state_machine, event
                ),
            ),
        ]
        super().__init__(
            state_name="stopping_paused_mission",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
