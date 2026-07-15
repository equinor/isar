from typing import TYPE_CHECKING, List

import isar.state_machine.states.going_to_lockdown as GoingToLockdown
import isar.state_machine.states.going_to_recharging as GoingToRecharging
import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.recharging_with_mission as RechargingWithMission
from isar.apis.models.models import ControlMissionResponse
from isar.eventhandlers.state import EventHandlerMapping, State, Transition
from isar.models.events import AbortedMission, EmptyMessage
from isar.services.utilities.mqtt_utilities import publish_mission_status
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.status import MissionStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class GoingToRechargingWithMission(State):

    def __init__(self, state_machine: "StateMachine", mission: AbortedMission):
        events = state_machine.events

        def _mission_failed_event_handler(
            error_message: ErrorMessage,
        ) -> Transition[InterventionNeeded.InterventionNeeded]:
            publish_mission_status(
                state_machine.mqtt_publisher,
                mission.id,
                MissionStatus.Failed,
                error_message,
            )
            return InterventionNeeded.transition("Return home to recharge failed")

        def _stop_mission_event_handler(
            stop_mission_id: str,
        ) -> Transition[GoingToRecharging.GoingToRecharging] | None:
            if mission.id == stop_mission_id or stop_mission_id == "":
                state_machine.events.api_requests.stop_mission.response.trigger_event(
                    ControlMissionResponse(success=True)
                )
                return GoingToRecharging.transition_to_existing_mission()
            else:
                state_machine.events.api_requests.stop_mission.response.trigger_event(
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
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition_and_start_return_home(
    mission: AbortedMission,
) -> Transition[GoingToRechargingWithMission]:
    def _transition(state_machine: "StateMachine") -> GoingToRechargingWithMission:
        if state_machine.events.robot_service_events.mission_failed.clear_event():
            state_machine.logger.warning("Mission failed had lingering event")
        if state_machine.events.robot_service_events.mission_succeeded.clear_event():
            state_machine.logger.warning("Mission succeeded had lingering event")
        state_machine.start_return_home_mission()
        return GoingToRechargingWithMission(state_machine, mission=mission)

    return _transition
