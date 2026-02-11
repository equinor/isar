from typing import TYPE_CHECKING, List

import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.lockdown as Lockdown
from isar.config.settings import settings
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.models.events import EmptyMessage
from isar.services.service_connections.persistent_memory import (
    RobotStartupMode,
    change_persistent_robot_state,
)
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage

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

        def _mission_success_event_handler(
            success: EmptyMessage,
        ) -> Transition[Lockdown.Lockdown]:
            state_machine.print_transitions()
            return Lockdown.transition()

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[ErrorMessage](
                name="mission_failed_event",
                event=events.robot_service_events.mission_failed,
                handler=_mission_failed_event_handler,
            ),
            EventHandlerMapping[ErrorMessage](
                name="mission_failed_to_resume",
                event=events.robot_service_events.mission_failed_to_resume,
                handler=_mission_failed_to_resume_event_handler,
            ),
            EventHandlerMapping[EmptyMessage](
                name="mission_succeeded_event",
                event=events.robot_service_events.mission_succeeded,
                handler=_mission_success_event_handler,
            ),
        ]
        super().__init__(
            state_name=States.GoingToLockdown,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition() -> Transition[GoingToLockdown]:
    def _transition(state_machine: "StateMachine") -> GoingToLockdown:
        if settings.USE_DB:
            change_persistent_robot_state(
                settings.ISAR_ID,
                value=RobotStartupMode.Lockdown,
            )
        return GoingToLockdown(state_machine)

    return _transition
