import isar.state_machine.states.going_to_lockdown_with_mission as GoingToLockdownWithMission
import isar.state_machine.states.going_to_recharging as GoingToRecharging
import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.recharging_with_mission as RechargingWithMission
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.mission import ReturnHomeMission
from robot_interface.models.mission.status import MissionStatus


def GoingToRechargingWithMission(events: Events, mission: AbortedMission) -> State:

    def _mission_failed_event_handler(
        error_message: ErrorMessage,
    ) -> Transition:
        events.mqtt_queue.publish_mission_status(
            mission.id,
            MissionStatus.Failed,
            error_message,
        )
        return InterventionNeeded.transition("Return home to recharge failed")

    def _stop_mission_event_handler(
        _: EmptyMessage,
    ) -> Transition | None:
        events.api_requests.stop_mission.response.trigger_event(
            ControlMissionResponse(success=True)
        )
        return GoingToRecharging.transition_to_existing_mission()

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[ErrorMessage](
            event=events.robot_service_events.mission_failed,
            handler=_mission_failed_event_handler,
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.robot_service_events.mission_succeeded,
            handler=lambda _: RechargingWithMission.transition(mission),
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.send_to_lockdown.request,
            handler=lambda _: GoingToLockdownWithMission.transition_to_existing_mission_and_report_to_api(
                mission
            ),
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.stop_mission.request,
            handler=_stop_mission_event_handler,
        ),
    ]
    return State(
        state_name=States.GoingToRechargingWithMission,
        signal_exit_event=events.signal_state_machine_exit,
        event_handler_mappings=event_handlers,
    )


def transition_and_start_return_home(
    mission: AbortedMission,
) -> Transition:
    def _transition(events: Events) -> State:
        events.robot_service_events.mission_failed.clear_event()
        events.robot_service_events.mission_succeeded.clear_event()
        events.robot_service_events.mission_started_successfully.clear_event()

        events.state_machine_events.start_mission.trigger_event(ReturnHomeMission())
        return GoingToRechargingWithMission(events, mission=mission)

    return _transition
