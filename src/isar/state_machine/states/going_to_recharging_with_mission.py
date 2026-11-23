import isar.state_machine.states.going_to_lockdown_with_mission as GoingToLockdownWithMission
import isar.state_machine.states.going_to_recharging as GoingToRecharging
import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.recharging_with_mission as RechargingWithMission
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import AbortedMission, EmptyMessage
from isar.models.mqtt_queue import MissionResultStatus
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
from robot_interface.models.mission.status import MissionStatus

state: StateDef[AbortedMission] = StateDef(
    name=States.GoingToRechargingWithMission,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.action_requests.return_home.failure,
            branches=(
                Branch(
                    InterventionNeeded.transition,
                    lambda _, __: "Return home to recharge failed",
                    side_effects=(
                        HandlerEffect(
                            OutputEvent.mqtt(lambda q: q.publish_mission_result),
                            lambda mission, error: MissionResultStatus(
                                mission.id, MissionStatus.Failed, error
                            ),
                        ),
                    ),
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.action_requests.return_home.success,
            branches=(
                Branch(RechargingWithMission.transition, forward_state_parameter),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.send_to_lockdown.request,
            branches=(
                Branch(
                    GoingToLockdownWithMission.transition_with_existing_return_home_and_respond_to_api,
                    forward_state_parameter,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.stop_mission.request,
            branches=(
                Branch(
                    GoingToRecharging.transition_with_existing_return_home,
                    side_effects=(
                        HandlerEffect(
                            OutputEvent.api_response(lambda a: a.stop_mission),
                            lambda _, __: ControlMissionResponse(success=True),
                        ),
                        HandlerEffect(
                            OutputEvent.mqtt(lambda q: q.publish_mission_result),
                            lambda mission, _: MissionResultStatus(
                                mission.id, MissionStatus.Cancelled
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)


transition_and_start_return_home: TransitionDef[AbortedMission, AbortedMission] = (
    TransitionDef(
        state,
        forward_transition_parameter,
        side_effects=(
            TransitionEffect(
                OutputEvent.robot_request(lambda a: a.return_home),
                lambda _: EmptyMessage(),
            ),
        ),
    )
)
