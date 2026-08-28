import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.lockdown as Lockdown
from isar.apis.models.models import LockdownResponse
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.mission import ReturnHomeMission


def GoingToLockdown(events: Events) -> State:

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[ErrorMessage](
            event=events.action_requests.execute_mission.failure,
            handler=lambda _: InterventionNeeded.transition("Lockdown mission failed"),
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.action_requests.resume_mission.failure,
            handler=lambda _: InterventionNeeded.transition(
                "Failed to resume return to home mission"
            ),
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.action_requests.execute_mission.success,
            handler=lambda _: Lockdown.transition_without_responding_to_api(),
        ),
    ]
    return State(
        state_name=States.GoingToLockdown,
        signal_exit_event=events.signal_state_machine_exit,
        event_handler_mappings=event_handlers,
    )


def transition_and_start_mission_and_report_to_api() -> Transition:
    def _transition(events: Events) -> State:
        events.api_requests.send_to_lockdown.response.trigger_event(
            LockdownResponse(lockdown_started=True)
        )

        events.action_requests.execute_mission.trigger_request(ReturnHomeMission())
        return GoingToLockdown(events)

    return _transition


def transition_to_existing_mission_and_report_to_api() -> Transition:
    def _transition(events: Events) -> State:
        events.api_requests.send_to_lockdown.response.trigger_event(
            LockdownResponse(lockdown_started=True)
        )
        return GoingToLockdown(events)

    return _transition
