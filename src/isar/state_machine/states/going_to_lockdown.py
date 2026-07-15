from typing import TYPE_CHECKING, List

import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.lockdown as Lockdown
from isar.apis.models.models import LockdownResponse
from isar.eventhandlers.state import EventHandlerMapping, State, Transition
from isar.models.events import EmptyMessage
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class GoingToLockdown(State):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[ErrorMessage](
                name="mission_failed_event",
                event=events.robot_service_events.mission_failed,
                handler=lambda _: InterventionNeeded.transition(
                    "Lockdown mission failed"
                ),
            ),
            EventHandlerMapping[EmptyMessage](
                name="mission_failed_to_resume",
                event=events.robot_service_events.mission_failed_to_resume,
                handler=lambda _: InterventionNeeded.transition(
                    "Failed to resume return to home mission"
                ),
            ),
            EventHandlerMapping[EmptyMessage](
                name="mission_succeeded_event",
                event=events.robot_service_events.mission_succeeded,
                handler=lambda _: Lockdown.transition_without_responding_to_api(),
            ),
        ]
        super().__init__(
            state_name=States.GoingToLockdown,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition_and_start_mission_and_report_to_api() -> Transition[GoingToLockdown]:
    def _transition(state_machine: "StateMachine") -> GoingToLockdown:
        state_machine.events.api_requests.send_to_lockdown.response.trigger_event(
            LockdownResponse(lockdown_started=True)
        )

        if state_machine.events.robot_service_events.mission_failed.clear_event():
            state_machine.logger.warning("Mission failed had lingering event")
        if state_machine.events.robot_service_events.mission_succeeded.clear_event():
            state_machine.logger.warning("Mission succeeded had lingering event")
        state_machine.start_return_home_mission()
        return GoingToLockdown(state_machine)

    return _transition


def transition_to_existing_mission_and_report_to_api() -> Transition[GoingToLockdown]:
    def _transition(state_machine: "StateMachine") -> GoingToLockdown:
        state_machine.events.api_requests.send_to_lockdown.response.trigger_event(
            LockdownResponse(lockdown_started=True)
        )
        return GoingToLockdown(state_machine)

    return _transition
