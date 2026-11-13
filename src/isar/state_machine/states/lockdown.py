import isar.state_machine.states.home as Home
from isar.apis.models.models import LockdownResponse
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
    events.api.respond(lambda r: r.release_from_lockdown, EmptyMessage())


state: StateDef[None] = StateDef(
    name=States.Lockdown,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.api_requests.release_from_lockdown.request,
            branches=(Branch(Home.transition, side_effect=_accept_release),),
        ),
    ),
)


def _respond(events: OutputEvents, _: None) -> None:
    events.api.respond(
        lambda r: r.send_to_lockdown, LockdownResponse(lockdown_started=True)
    )


transition: TransitionDef[None, None] = TransitionDef(state, forward)
transition_and_respond_to_api: TransitionDef[None, None] = TransitionDef(
    state, forward, side_effect=_respond
)
