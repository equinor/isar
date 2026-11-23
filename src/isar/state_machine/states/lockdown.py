import isar.state_machine.states.home as Home
from isar.apis.models.models import LockdownResponse
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
    name=States.Lockdown,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.api_requests.release_from_lockdown.request,
            branches=(
                Branch(
                    Home.transition,
                    side_effects=(
                        HandlerEffect(
                            OutputEvent.api_response(lambda a: a.release_from_lockdown),
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
            OutputEvent.api_response(lambda a: a.send_to_lockdown),
            lambda _: LockdownResponse(lockdown_started=True),
        ),
    ),
)
