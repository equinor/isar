import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.lockdown_with_mission as LockdownWithMission
from isar.apis.models.models import LockdownResponse
from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.state_machine.state import (
    EventHandlerMapping,
    StateDef,
    Transition,
    state_definition,
)
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.status import MissionStatus


@state_definition
def GoingToLockdownWithMission(events: Events, mission: AbortedMission) -> StateDef:

    def _lockdown_mission_failed(error_message: ErrorMessage) -> Transition:
        events.mqtt_queue.publish_mission_status(
            mission.id,
            MissionStatus.Failed,
            error_message,
        )
        return InterventionNeeded.transition(events, "Lockdown mission failed")

    def _lockdown_mission_failed_to_resume(_: EmptyMessage) -> Transition:
        events.mqtt_queue.publish_mission_status(
            mission.id,
            MissionStatus.Failed,
            ErrorMessage(
                ErrorReason.RobotActionException, "Failed to resume lockdown mission"
            ),
        )
        return InterventionNeeded.transition(
            events, "Failed to resume return to home mission"
        )

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[ErrorMessage](
            event=events.action_requests.return_home.failure,
            handler=_lockdown_mission_failed,
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.action_requests.resume_mission.failure,
            handler=_lockdown_mission_failed_to_resume,
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.action_requests.return_home.success,
            handler=lambda _: LockdownWithMission.transition(events, mission),
        ),
    ]
    return StateDef(
        name=States.GoingToLockdownWithMission,
        handlers=event_handlers,
    )


def transition_and_start_mission_and_report_to_api(
    events: Events,
    mission: AbortedMission,
) -> Transition:
    def _side_effect(events: Events) -> None:
        events.api_requests.send_to_lockdown.trigger_response(
            LockdownResponse(lockdown_started=True)
        )
        events.action_requests.return_home.trigger_request(EmptyMessage())

    return Transition(GoingToLockdownWithMission(events, mission), _side_effect)


def transition_to_existing_mission_and_report_to_api(
    events: Events,
    mission: AbortedMission,
) -> Transition:
    def _side_effect(events: Events) -> None:
        events.api_requests.send_to_lockdown.trigger_response(
            LockdownResponse(lockdown_started=True)
        )

    return Transition(GoingToLockdownWithMission(events, mission), _side_effect)
