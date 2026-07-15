from typing import TYPE_CHECKING, List

import isar.state_machine.states.home as Home
from isar.apis.models.models import LockdownResponse
from isar.models.events import EmptyMessage
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Lockdown(State):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

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
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition_without_responding_to_api() -> Transition[Lockdown]:
    def _transition(state_machine: "StateMachine") -> Lockdown:
        return Lockdown(state_machine)

    return _transition


def transition_and_respond_to_api() -> Transition[Lockdown]:
    def _transition(state_machine: "StateMachine") -> Lockdown:
        state_machine.events.api_requests.send_to_lockdown.response.trigger_event(
            LockdownResponse(lockdown_started=True)
        )
        return Lockdown(state_machine)

    return _transition
