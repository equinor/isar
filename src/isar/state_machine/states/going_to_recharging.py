from typing import TYPE_CHECKING, List, Optional, Union

import isar.state_machine.states.going_to_lockdown as GoingToLockdown
import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.recharging as Recharging
from isar.apis.models.models import LockdownResponse
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.status import MissionStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class GoingToRecharging(State):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

        def _mission_failed_event_handler(
            mission_failed: ErrorMessage,
        ) -> Transition[InterventionNeeded.InterventionNeeded]:
            state_machine.logger.warning(
                f"Failed to go to recharging because: "
                f"{mission_failed.error_description}"
            )
            state_machine.publish_intervention_needed(
                error_message="Return home to recharge failed."
            )
            state_machine.print_transitions()
            return InterventionNeeded.transition()

        def _mission_status_event_handler(
            mission_status: MissionStatus,
        ) -> Optional[
            Union[
                Transition[InterventionNeeded.InterventionNeeded],
                Transition[Recharging.Recharging],
            ]
        ]:
            if not mission_status or mission_status in [
                MissionStatus.InProgress,
                MissionStatus.NotStarted,
                MissionStatus.Paused,
            ]:
                return None

            if mission_status != MissionStatus.Successful:
                state_machine.logger.warning(
                    "Failed to return home. Mission reported as failed."
                )
                state_machine.publish_intervention_needed(
                    error_message="Return home to recharge failed."
                )
                state_machine.print_transitions()
                return InterventionNeeded.transition()

            return Recharging.transition()

        def _send_to_lockdown_event_handler(
            should_lockdown: bool,
        ) -> Transition[GoingToLockdown.GoingToLockdown]:
            events.api_requests.send_to_lockdown.response.trigger_event(
                LockdownResponse(lockdown_started=True)
            )
            return GoingToLockdown.transition()

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="mission_failed_event",
                event=events.robot_service_events.mission_failed,
                handler=_mission_failed_event_handler,
            ),
            EventHandlerMapping(
                name="mission_status_event",
                event=events.robot_service_events.mission_status_updated,
                handler=_mission_status_event_handler,
            ),
            EventHandlerMapping(
                name="send_to_lockdown_event",
                event=events.api_requests.send_to_lockdown.request,
                handler=_send_to_lockdown_event_handler,
            ),
        ]
        super().__init__(
            state_name=States.GoingToRecharging,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition() -> Transition[GoingToRecharging]:
    def _transition(state_machine: "StateMachine"):
        return GoingToRecharging(state_machine)

    return _transition
