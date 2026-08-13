import isar.state_machine.states.home as Home
from isar.apis.models.models import LockdownResponse
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States


def Lockdown(events: Events) -> State:

    def _release_from_lockdown_handler(
        _: EmptyMessage,
    ) -> Transition:
        events.api_requests.release_from_lockdown.response.trigger_event(EmptyMessage())
        return Home.transition()

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.release_from_lockdown.request,
            handler=_release_from_lockdown_handler,
        ),
    ]

    return State(
        state_name=States.Lockdown,
        signal_exit_event=events.signal_state_machine_exit,
        event_handler_mappings=event_handlers,
    )


def transition_without_responding_to_api() -> Transition:
    def _transition(events: Events) -> State:
        return Lockdown(events)

    return _transition


def transition_and_respond_to_api() -> Transition:
    def _transition(events: Events) -> State:
        events.api_requests.send_to_lockdown.response.trigger_event(
            LockdownResponse(lockdown_started=True)
        )
        return Lockdown(events)

    return _transition
