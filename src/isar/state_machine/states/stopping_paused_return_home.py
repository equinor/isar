import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.monitor as Monitor
from isar.apis.models.models import MissionStartResponse
from isar.models.events import EmptyMessage
from isar.state_machine.output_events import OutputEvent
from isar.state_machine.state import (
    Branch,
    EventHandler,
    StateDef,
    TransitionDef,
    TransitionEffect,
    forward_state_parameter,
    forward_transition_parameter,
)
from isar.state_machine.states_enum import States
from robot_interface.models.mission.mission import Mission

state: StateDef[Mission] = StateDef(
    name=States.StoppingPausedReturnHome,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.action_requests.stop_mission.failure,
            branches=(
                Branch(
                    InterventionNeeded.transition,
                    lambda _, __: "Failed to stop paused return home mission",
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.action_requests.stop_mission.success,
            branches=(
                Branch(Monitor.transition_and_start_mission, forward_state_parameter),
            ),
        ),
    ),
)


transition_and_stop_return_home_and_respond_to_api: TransitionDef[Mission, Mission] = (
    TransitionDef(
        state,
        forward_transition_parameter,
        side_effects=(
            TransitionEffect(
                OutputEvent.robot_request(lambda a: a.stop_mission),
                lambda _: EmptyMessage(),
            ),
            TransitionEffect(
                OutputEvent.api_response(lambda a: a.start_mission),
                lambda mission: MissionStartResponse(
                    mission_id=mission.id, mission_started=True
                ),
            ),
        ),
    )
)
