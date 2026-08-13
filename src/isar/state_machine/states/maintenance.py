import isar.state_machine.states.unknown_status as UnknownStatus
from isar.apis.models.models import MaintenanceResponse
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States


def Maintenance(events: Events) -> State:

    def _release_from_maintenance_handler(
        _: EmptyMessage,
    ) -> Transition:
        events.api_requests.release_from_maintenance_mode.response.trigger_event(
            EmptyMessage()
        )

        return UnknownStatus.transition()

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.release_from_maintenance_mode.request,
            handler=_release_from_maintenance_handler,
        ),
    ]

    return State(
        state_name=States.Maintenance,
        signal_exit_event=events.signal_state_machine_exit,
        event_handler_mappings=event_handlers,
    )


def transition_and_reply_to_API() -> Transition:
    def _transition(events: Events) -> State:
        events.api_requests.set_maintenance_mode.response.trigger_event(
            MaintenanceResponse(is_maintenance_mode=True)
        )
        return Maintenance(events)

    return _transition


def transition_without_replying_to_API() -> Transition:
    def _transition(events: Events) -> State:
        return Maintenance(events)

    return _transition
