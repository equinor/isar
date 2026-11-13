import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.intervention_needed as InterventionNeeded
from isar.apis.models.models import ControlMissionResponse
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

state: StateDef[None] = StateDef(
    name=States.StoppingUnknownMission,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.action_requests.stop_mission.failure,
            branches=(
                Branch(
                    InterventionNeeded.transition,
                    lambda _, __: "Failed to stop unknown mission",
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.action_requests.stop_mission.success,
            branches=(Branch(AwaitNextMission.transition),),
        ),
    ),
)


def _request_stop(events: OutputEvents, _: None) -> None:
    events.robot.request(lambda a: a.stop_mission, EmptyMessage())


def _request_stop_and_respond(events: OutputEvents, _: None) -> None:
    _request_stop(events, None)
    events.api.respond(lambda r: r.stop_mission, ControlMissionResponse(success=True))


transition_and_stop_mission: TransitionDef[None, None] = TransitionDef(
    state, forward, side_effect=_request_stop
)
transition_and_stop_mission_and_respond_to_api: TransitionDef[None, None] = (
    TransitionDef(state, forward, side_effect=_request_stop_and_respond)
)
