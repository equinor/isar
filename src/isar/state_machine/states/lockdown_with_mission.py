import isar.state_machine.states.monitor as Monitor
from isar.apis.models.models import LockdownResponse
from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.state_machine.state import (
    EventHandlerMapping,
    StateDef,
    Transition,
    state_definition,
)
from isar.state_machine.states_enum import States


@state_definition
def LockdownWithMission(events: Events, mission: AbortedMission) -> StateDef:

    def _release_from_lockdown_handler(
        _: EmptyMessage,
    ) -> Transition:
        events.api_requests.release_from_lockdown.trigger_response(EmptyMessage())
        return Monitor.transition_and_start_mission(events, mission)

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.release_from_lockdown.request,
            handler=_release_from_lockdown_handler,
        ),
    ]

    return StateDef(
        name=States.LockdownWithMission,
        handlers=event_handlers,
    )


def transition(events: Events, mission: AbortedMission) -> Transition:
    def _side_effect(events: Events) -> None:
        events.api_requests.send_to_lockdown.trigger_response(
            LockdownResponse(lockdown_started=True)
        )

    return Transition(LockdownWithMission(events, mission), _side_effect)
