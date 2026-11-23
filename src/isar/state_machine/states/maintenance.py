import isar.state_machine.states.unknown_status as UnknownStatus
from isar.apis.models.models import MaintenanceResponse
from isar.models.events import EmptyMessage
from isar.state_machine.output_events import OutputEvent
from isar.state_machine.state import (
    Branch,
    EventHandler,
    HandlerEffect,
    StateDef,
    TransitionDef,
    TransitionEffect,
)
from isar.state_machine.states_enum import States

state: StateDef[None] = StateDef(
    name=States.Maintenance,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.api_requests.release_from_maintenance_mode.request,
            branches=(
                Branch(
                    UnknownStatus.transition,
                    side_effects=(
                        HandlerEffect(
                            OutputEvent.api_response(
                                lambda a: a.release_from_maintenance_mode
                            ),
                            lambda _, __: EmptyMessage(),
                        ),
                    ),
                ),
            ),
        ),
    ),
)


transition: TransitionDef[None, None] = TransitionDef(state)
transition_and_respond_to_api: TransitionDef[None, None] = TransitionDef(
    state,
    side_effects=(
        TransitionEffect(
            OutputEvent.api_response(lambda a: a.set_maintenance_mode),
            lambda _: MaintenanceResponse(is_maintenance_mode=True),
        ),
    ),
)
