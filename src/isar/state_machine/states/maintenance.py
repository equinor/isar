import isar.state_machine.states.unknown_status as UnknownStatus
from isar.apis.models.models import MaintenanceResponse
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import (
    EventHandlerMapping,
    StateDef,
    Transition,
    state_definition,
)
from isar.state_machine.states_enum import States


@state_definition
def Maintenance(events: Events) -> StateDef:

    def _release_from_maintenance_handler(
        _: EmptyMessage,
    ) -> Transition:
        events.api_requests.release_from_maintenance_mode.trigger_response(
            EmptyMessage()
        )

        return UnknownStatus.transition()

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.release_from_maintenance_mode.request,
            handler=_release_from_maintenance_handler,
        ),
    ]

    return StateDef(
        name=States.Maintenance,
        handlers=event_handlers,
    )


def transition_and_reply_to_API() -> Transition:
    def _transition(events: Events) -> StateDef:
        events.api_requests.set_maintenance_mode.trigger_response(
            MaintenanceResponse(is_maintenance_mode=True)
        )
        return Maintenance(events)

    return _transition


def transition_without_replying_to_API() -> Transition:
    return Maintenance
