from typing import List

import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.lockdown as Lockdown
from isar.apis.models.models import LockdownResponse
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.mission import ReturnHomeMission


class GoingToLockdown(State):

    def __init__(self, events: Events):

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
            signal_exit_event=events.signal_state_machine_exit,
            event_handler_mappings=event_handlers,
        )


def transition_and_start_mission_and_report_to_api() -> Transition[GoingToLockdown]:
    def _transition(events: Events) -> GoingToLockdown:
        events.api_requests.send_to_lockdown.response.trigger_event(
            LockdownResponse(lockdown_started=True)
        )

        events.robot_service_events.mission_failed.clear_event()
        events.robot_service_events.mission_succeeded.clear_event()

        events.state_machine_events.start_mission.trigger_event(ReturnHomeMission())
        return GoingToLockdown(events)

    return _transition


def transition_to_existing_mission_and_report_to_api() -> Transition[GoingToLockdown]:
    def _transition(events: Events) -> GoingToLockdown:
        events.api_requests.send_to_lockdown.response.trigger_event(
            LockdownResponse(lockdown_started=True)
        )
        return GoingToLockdown(events)

    return _transition
