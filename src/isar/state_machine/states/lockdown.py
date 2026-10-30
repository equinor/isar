import isar.state_machine.states.home as Home
from isar.apis.models.models import LockdownResponse
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import (
    EventHandlerMapping,
    StateDef,
    Transition,
    state_definition,
)
from isar.state_machine.states_enum import States


@state_definition
def Lockdown(events: Events) -> StateDef:

    def _release_from_lockdown_handler(
        _: EmptyMessage,
    ) -> Transition:
        events.api_requests.release_from_lockdown.trigger_response(EmptyMessage())
        return Home.transition(events)

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.release_from_lockdown.request,
            handler=_release_from_lockdown_handler,
        ),
    ]

    return StateDef(
        name=States.Lockdown,
        handlers=event_handlers,
    )


def transition_without_responding_to_api(events: Events) -> Transition:
    return Transition(Lockdown(events))


def transition_and_respond_to_api(events: Events) -> Transition:
    def _side_effect(events: Events) -> None:
        events.api_requests.send_to_lockdown.trigger_response(
            LockdownResponse(lockdown_started=True)
        )

    return Transition(Lockdown(events), _side_effect)
