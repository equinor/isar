import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.intervention_needed as InterventionNeeded
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States


def StoppingUnknownMission(events: Events) -> State:

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.action_requests.stop_mission.failure,
            handler=lambda _: InterventionNeeded.transition(
                "Failed to stop unknown mission"
            ),
        ),
        EventHandlerMapping[AbortedMission | EmptyMessage](
            event=events.action_requests.stop_mission.success,
            handler=lambda _: AwaitNextMission.transition(),
        ),
    ]
    return State(
        state_name=States.StoppingUnknownMission,
        signal_exit_event=events.signal_state_machine_exit,
        event_handler_mappings=event_handlers,
    )


def transition() -> Transition:
    def _transition(events: Events) -> State:
        events.action_requests.stop_mission.trigger_request(EmptyMessage())
        return StoppingUnknownMission(events)

    return _transition


def transition_and_respond_to_API() -> Transition:
    def _transition(events: Events) -> State:
        events.action_requests.stop_mission.trigger_request(EmptyMessage())
        events.api_requests.stop_mission.response.trigger_event(
            ControlMissionResponse(success=True)
        )
        return StoppingUnknownMission(events)

    return _transition
