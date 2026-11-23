import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.paused as Paused
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import EmptyMessage
from isar.state_machine.output_events import OutputEvent
from isar.state_machine.state import (
    Branch,
    EventHandler,
    HandlerEffect,
    StateDef,
    TransitionDef,
    TransitionEffect,
    forward_state_parameter,
    forward_transition_parameter,
)
from isar.state_machine.states_enum import States

state: StateDef[str] = StateDef(
    name=States.Pausing,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.action_requests.pause_mission.failure,
            branches=(
                Branch(
                    Monitor.transition_with_existing_mission, forward_state_parameter
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.action_requests.pause_mission.success,
            branches=(
                Branch(
                    Paused.transition,
                    forward_state_parameter,
                    side_effects=(
                        HandlerEffect(
                            OutputEvent.mqtt(lambda q: q.publish_mission_paused),
                            lambda mission_id, _: mission_id,
                        ),
                    ),
                ),
            ),
        ),
    ),
)


transition_and_pause_mission_and_respond_to_api: TransitionDef[str, str] = (
    TransitionDef(
        state,
        forward_transition_parameter,
        side_effects=(
            TransitionEffect(
                OutputEvent.api_response(lambda a: a.pause_mission),
                lambda _: ControlMissionResponse(success=True),
            ),
            TransitionEffect(
                OutputEvent.robot_request(lambda a: a.pause_mission),
                lambda _: EmptyMessage(),
            ),
        ),
    )
)
