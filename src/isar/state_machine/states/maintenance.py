import isar.state_machine.states.unknown_status as UnknownStatus
from isar.apis.models.models import MaintenanceResponse
from isar.models.events import EmptyMessage
from isar.state_machine.capabilities import OutputEvents
from isar.state_machine.state import (
    Branch,
    EventHandler,
    StateDef,
    TransitionDef,
    forward,
)
from isar.state_machine.states_enum import States


def _accept_release(events: OutputEvents, _: None, __: EmptyMessage) -> None:
    events.api.respond(lambda r: r.release_from_maintenance_mode, EmptyMessage())


state: StateDef[None] = StateDef(
    name=States.Maintenance,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.api_requests.release_from_maintenance_mode.request,
            branches=(Branch(UnknownStatus.transition, side_effect=_accept_release),),
        ),
    ),
)


def _respond(events: OutputEvents, _: None) -> None:
    events.api.respond(
        lambda r: r.set_maintenance_mode,
        MaintenanceResponse(is_maintenance_mode=True),
    )


transition: TransitionDef[None, None] = TransitionDef(state, forward)
transition_and_respond_to_api: TransitionDef[None, None] = TransitionDef(
    state, forward, side_effect=_respond
)
