from typing import List

import isar.state_machine.states.going_to_lockdown as GoingToLockdown
import isar.state_machine.states.going_to_recharging as GoingToRecharging
import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.recharging_with_mission as RechargingWithMission
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.services.utilities.mqtt_utilities import publish_mission_status
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.mission import ReturnHomeMission
from robot_interface.models.mission.status import MissionStatus


class GoingToRechargingWithMission(State):

    def __init__(self, events: Events, mission: AbortedMission):

        def _mission_failed_event_handler(
            error_message: ErrorMessage,
        ) -> Transition[InterventionNeeded.InterventionNeeded]:
            publish_mission_status(
                events.mqtt_queue,
                mission.id,
                MissionStatus.Failed,
                error_message,
            )
            return InterventionNeeded.transition("Return home to recharge failed")

        def _stop_mission_event_handler(
            stop_mission_id: str,
        ) -> Transition[GoingToRecharging.GoingToRecharging] | None:
            if mission.id == stop_mission_id or stop_mission_id == "":
                events.api_requests.stop_mission.response.trigger_event(
                    ControlMissionResponse(success=True)
                )
                return GoingToRecharging.transition_to_existing_mission()
            else:
                events.api_requests.stop_mission.response.trigger_event(
                    ControlMissionResponse(
                        success=False, failure_reason="Mission not found"
                    )
                )
                return None

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[ErrorMessage](
                name="mission_failed_event",
                event=events.robot_service_events.mission_failed,
                handler=_mission_failed_event_handler,
            ),
            EventHandlerMapping[EmptyMessage](
                name="mission_succeeded_event",
                event=events.robot_service_events.mission_succeeded,
                handler=lambda _: RechargingWithMission.transition(mission),
            ),
            EventHandlerMapping[EmptyMessage](
                name="send_to_lockdown_event",
                event=events.api_requests.send_to_lockdown.request,
                handler=lambda _: GoingToLockdown.transition_to_existing_mission_and_report_to_api(),
            ),
            EventHandlerMapping[str](
                name="stop_mission_event",
                event=events.api_requests.stop_mission.request,
                handler=_stop_mission_event_handler,
            ),
        ]
        super().__init__(
            state_name=States.GoingToRechargingWithMission,
            signal_exit_event=events.signal_state_machine_exit,
            event_handler_mappings=event_handlers,
        )


def transition_and_start_return_home(
    mission: AbortedMission,
) -> Transition[GoingToRechargingWithMission]:
    def _transition(events: Events) -> GoingToRechargingWithMission:
        events.robot_service_events.mission_failed.clear_event()
        events.robot_service_events.mission_succeeded.clear_event()

        events.state_machine_events.start_mission.trigger_event(ReturnHomeMission())
        return GoingToRechargingWithMission(events, mission=mission)

    return _transition
