from typing import TYPE_CHECKING, List

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.communication.queues.queue_utils import check_for_event

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Paused(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="stop_mission_event",
                event=events.api_requests.stop_mission.input,
                handler=lambda event: state_machine.stop if check_for_event(event) else None,  # type: ignore
            ),
            EventHandlerMapping(
                name="resume_mission_event",
                event=events.api_requests.resume_mission.input,
                handler=lambda event: state_machine.resume if check_for_event(event) else None,  # type: ignore
            ),
        ]
        super().__init__(
            state_name="paused",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
