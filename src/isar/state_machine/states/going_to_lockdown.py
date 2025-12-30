from typing import TYPE_CHECKING, List, Optional, Union

import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.lockdown as Lockdown
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from isar.state_machine.utils.common_event_handlers import mission_started_event_handler
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.status import MissionStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class GoingToLockdown(State):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

        def _mission_failed_event_handler(
            mission_failed: ErrorMessage,
        ) -> Transition[InterventionNeeded.InterventionNeeded]:
            state_machine.logger.warning(
                f"Failed to go to lockdown because: "
                f"{mission_failed.error_description}"
            )
            state_machine.publish_intervention_needed(
                error_message="Lockdown mission failed."
            )
            return InterventionNeeded.transition()

        def _mission_failed_to_resume_event_handler(
            mission_failed_to_resume: ErrorMessage,
        ) -> Transition[InterventionNeeded.InterventionNeeded]:
            state_machine.logger.warning(
                f"Failed to resume return to home mission and going to lockdown because: "
                f"{mission_failed_to_resume.error_description or ''}"
            )
            return InterventionNeeded.transition()

        def _mission_status_event_handler(
            mission_status: MissionStatus,
        ) -> Optional[
            Union[
                Transition[InterventionNeeded.InterventionNeeded],
                Transition[Lockdown.Lockdown],
            ]
        ]:
            if mission_status and mission_status not in [
                MissionStatus.InProgress,
                MissionStatus.NotStarted,
                MissionStatus.Paused,
            ]:
                if mission_status != MissionStatus.Successful:
                    state_machine.publish_intervention_needed(
                        error_message="Lockdown mission failed."
                    )
                    return InterventionNeeded.transition()

                state_machine.print_transitions()
                return Lockdown.transition()
            return None

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="mission_started_event",
                event=events.robot_service_events.mission_started,
                handler=lambda event: mission_started_event_handler(
                    state_machine, event
                ),
            ),
            EventHandlerMapping(
                name="mission_failed_event",
                event=events.robot_service_events.mission_failed,
                handler=_mission_failed_event_handler,
            ),
            EventHandlerMapping(
                name="mission_failed_to_resume",
                event=events.robot_service_events.mission_failed_to_resume,
                handler=_mission_failed_to_resume_event_handler,
            ),
            EventHandlerMapping(
                name="mission_status_event",
                event=events.robot_service_events.mission_status_updated,
                handler=_mission_status_event_handler,
            ),
        ]
        super().__init__(
            state_name=States.GoingToLockdown,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition() -> Transition[GoingToLockdown]:
    def _transition(state_machine: "StateMachine"):
        return GoingToLockdown(state_machine)

    return _transition
