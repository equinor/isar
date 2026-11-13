import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.lockdown_with_mission as LockdownWithMission
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
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.status import MissionStatus


def _publish_lockdown_failed(
    events: OutputEvents, mission: AbortedMission, error: ErrorMessage
) -> None:
    events.mqtt.publish_mission_status(mission.id, MissionStatus.Failed, error)


def _publish_resume_failed(
    events: OutputEvents, mission: AbortedMission, _: EmptyMessage
) -> None:
    events.mqtt.publish_mission_status(
        mission.id,
        MissionStatus.Failed,
        ErrorMessage(
            ErrorReason.RobotActionException, "Failed to resume lockdown mission"
        ),
    )


state: StateDef[AbortedMission] = StateDef(
    name=States.GoingToLockdownWithMission,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.action_requests.return_home.failure,
            branches=(
                Branch(
                    InterventionNeeded.transition,
                    lambda _, __: "Lockdown mission failed",
                    side_effect=_publish_lockdown_failed,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.action_requests.resume_mission.failure,
            branches=(
                Branch(
                    InterventionNeeded.transition,
                    lambda _, __: "Failed to resume return to home mission",
                    side_effect=_publish_resume_failed,
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


def _respond(events: OutputEvents, _: AbortedMission) -> None:
    events.api.respond(
        lambda r: r.send_to_lockdown, LockdownResponse(lockdown_started=True)
    )


def _respond_and_request_return_home(
    events: OutputEvents, mission: AbortedMission
) -> None:
    _respond(events, mission)
    events.robot.request(lambda a: a.return_home, EmptyMessage())


transition_with_existing_return_home_and_respond_to_api: TransitionDef[
    AbortedMission, AbortedMission
] = TransitionDef(state, forward, side_effect=_respond)
transition_and_start_return_home_and_respond_to_api: TransitionDef[
    AbortedMission, AbortedMission
] = TransitionDef(state, forward, side_effect=_respond_and_request_return_home)
