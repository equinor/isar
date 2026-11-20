import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.lockdown_with_mission as LockdownWithMission
from isar.apis.models.models import LockdownResponse
from isar.models.events import AbortedMission, EmptyMessage
from isar.models.mqtt_queue import MissionStatusUpdate
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
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.status import MissionStatus

state: StateDef[AbortedMission] = StateDef(
    name=States.GoingToLockdownWithMission,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.action_requests.return_home.failure,
            branches=(
                Branch(
                    InterventionNeeded.transition,
                    lambda _, __: "Lockdown mission failed",
                    effects=(
                        HandlerEffect(
                            lambda e: e.mqtt_queue.publish_mission_result,
                            lambda mission, error: MissionStatusUpdate(
                                mission.id, MissionStatus.Failed, error
                            ),
                        ),
                    ),
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.action_requests.resume_mission.failure,
            branches=(
                Branch(
                    InterventionNeeded.transition,
                    lambda _, __: "Failed to resume return to home mission",
                    effects=(
                        HandlerEffect(
                            lambda e: e.mqtt_queue.publish_mission_result,
                            lambda mission, _: MissionStatusUpdate(
                                mission.id,
                                MissionStatus.Failed,
                                ErrorMessage(
                                    ErrorReason.RobotActionException,
                                    "Failed to resume lockdown mission",
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.action_requests.return_home.success,
            branches=(
                Branch(
                    LockdownWithMission.transition_and_respond_to_api,
                    forward_state_parameter,
                ),
            ),
        ),
    ),
)


_respond: TransitionEffect[AbortedMission] = TransitionEffect(
    lambda e: e.api_requests.send_to_lockdown.trigger_response,
    lambda _: LockdownResponse(lockdown_started=True),
)
_request_return_home: TransitionEffect[AbortedMission] = TransitionEffect(
    lambda e: e.action_requests.return_home.trigger_request,
    lambda _: EmptyMessage(),
)

transition_with_existing_return_home_and_respond_to_api: TransitionDef[
    AbortedMission, AbortedMission
] = TransitionDef(state, forward_transition_parameter, effects=(_respond,))
transition_and_start_return_home_and_respond_to_api: TransitionDef[
    AbortedMission, AbortedMission
] = TransitionDef(
    state, forward_transition_parameter, effects=(_respond, _request_return_home)
)
