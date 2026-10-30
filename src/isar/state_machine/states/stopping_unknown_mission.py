import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.intervention_needed as InterventionNeeded
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.state_machine.state import (
    EventHandlerMapping,
    StateDef,
    Transition,
    state_definition,
)
from isar.state_machine.states_enum import States


@state_definition
def StoppingUnknownMission(events: Events) -> StateDef:

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.action_requests.stop_mission.failure,
            handler=lambda _: InterventionNeeded.transition(
                events, "Failed to stop unknown mission"
            ),
        ),
        EventHandlerMapping[AbortedMission | EmptyMessage](
            event=events.action_requests.stop_mission.success,
            handler=lambda _: AwaitNextMission.transition(events),
        ),
    ]
    return StateDef(
        name=States.StoppingUnknownMission,
        handlers=event_handlers,
    )


def transition(events: Events) -> Transition:
    def _side_effect(events: Events) -> None:
        events.action_requests.stop_mission.trigger_request(EmptyMessage())

    return Transition(StoppingUnknownMission(events), _side_effect)


def transition_and_respond_to_API(events: Events) -> Transition:
    def _side_effect(events: Events) -> None:
        events.action_requests.stop_mission.trigger_request(EmptyMessage())
        events.api_requests.stop_mission.trigger_response(
            ControlMissionResponse(success=True)
        )

    return Transition(StoppingUnknownMission(events), _side_effect)
