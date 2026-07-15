from typing import List

import isar.state_machine.states.home as Home
from isar.apis.models.models import LockdownResponse
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States


class Lockdown(State):

    def __init__(self, events: Events):

        def _release_from_lockdown_handler(
            should_release_from_lockdown: EmptyMessage,
        ) -> Transition[Home.Home]:
            events.api_requests.release_from_lockdown.response.trigger_event(
                EmptyMessage()
            )
            return Home.transition()

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[EmptyMessage](
                name="release_from_lockdown",
                event=events.api_requests.release_from_lockdown.request,
                handler=_release_from_lockdown_handler,
            ),
        ]

        super().__init__(
            state_name=States.Lockdown,
            signal_exit_event=events.signal_state_machine_exit,
            event_handler_mappings=event_handlers,
        )


def transition_without_responding_to_api() -> Transition[Lockdown]:
    def _transition(events: Events) -> Lockdown:
        return Lockdown(events)

    return _transition


def transition_and_respond_to_api() -> Transition[Lockdown]:
    def _transition(events: Events) -> Lockdown:
        events.api_requests.send_to_lockdown.response.trigger_event(
            LockdownResponse(lockdown_started=True)
        )
        return Lockdown(events)

    return _transition
