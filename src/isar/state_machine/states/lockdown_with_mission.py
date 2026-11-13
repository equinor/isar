import isar.state_machine.states.monitor as Monitor
from isar.apis.models.models import LockdownResponse
from isar.models.events import AbortedMission, EmptyMessage
from isar.state_machine.capabilities import OutputEvents
from isar.state_machine.state import (
    Branch,
    EventHandler,
    StateDef,
    TransitionDef,
    forward,
    forward_state_parameter,
)
from isar.state_machine.states_enum import States


def _accept_release(events: OutputEvents, _: AbortedMission, __: EmptyMessage) -> None:
    events.api.respond(lambda r: r.release_from_lockdown, EmptyMessage())


state: StateDef[AbortedMission] = StateDef(
    name=States.LockdownWithMission,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.api_requests.release_from_lockdown.request,
            branches=(
                Branch(
                    Monitor.transition_and_start_mission,
                    forward_state_parameter,
                    side_effect=_accept_release,
                ),
            ),
        ),
    ),
)


def _respond(events: OutputEvents, _: AbortedMission) -> None:
    events.api.respond(
        lambda r: r.send_to_lockdown, LockdownResponse(lockdown_started=True)
    )


transition_and_respond_to_api: TransitionDef[AbortedMission, AbortedMission] = (
    TransitionDef(state, forward, side_effect=_respond)
)
