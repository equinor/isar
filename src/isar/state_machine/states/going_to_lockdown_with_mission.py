import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.lockdown_with_mission as LockdownWithMission
from isar.apis.models.models import LockdownResponse
from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.mission import ReturnHomeMission
from robot_interface.models.mission.status import MissionStatus


def GoingToLockdownWithMission(events: Events, mission: AbortedMission) -> State:

    def _lockdown_mission_failed(error_message: ErrorMessage) -> Transition:
        events.mqtt_queue.publish_mission_status(
            mission.id,
            MissionStatus.Failed,
            error_message,
        )
        return InterventionNeeded.transition("Lockdown mission failed")

    def _lockdown_mission_failed_to_resume(_: EmptyMessage) -> Transition:
        events.mqtt_queue.publish_mission_status(
            mission.id,
            MissionStatus.Failed,
            ErrorMessage(
                ErrorReason.RobotActionException, "Failed to resume lockdown mission"
            ),
        )
        return InterventionNeeded.transition("Failed to resume return to home mission")

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[ErrorMessage](
            event=events.action_requests.execute_mission.failure,
            handler=_lockdown_mission_failed,
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.action_requests.resume_mission.failure,
            handler=_lockdown_mission_failed_to_resume,
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.action_requests.execute_mission.success,
            handler=lambda _: LockdownWithMission.transition(mission),
        ),
    ]
    return State(
        state_name=States.GoingToLockdownWithMission,
        signal_exit_event=events.signal_state_machine_exit,
        event_handler_mappings=event_handlers,
    )


def transition_and_start_mission_and_report_to_api(
    mission: AbortedMission,
) -> Transition:
    def _transition(events: Events) -> State:
        events.api_requests.send_to_lockdown.response.trigger_event(
            LockdownResponse(lockdown_started=True)
        )

        events.action_requests.execute_mission.trigger_request(ReturnHomeMission())
        return GoingToLockdownWithMission(events, mission)

    return _transition


def transition_to_existing_mission_and_report_to_api(
    mission: AbortedMission,
) -> Transition:
    def _transition(events: Events) -> State:
        events.api_requests.send_to_lockdown.response.trigger_event(
            LockdownResponse(lockdown_started=True)
        )
        return GoingToLockdownWithMission(events, mission)

    return _transition
