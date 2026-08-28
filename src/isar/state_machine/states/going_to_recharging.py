import isar.state_machine.states.going_to_lockdown as GoingToLockdown
import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.recharging as Recharging
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.mission import ReturnHomeMission


def GoingToRecharging(events: Events) -> State:

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[ErrorMessage](
            event=events.action_requests.execute_mission.failure,
            handler=lambda _: InterventionNeeded.transition(
                "Return home to recharge failed"
            ),
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.action_requests.execute_mission.success,
            handler=lambda _: Recharging.transition(),
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.send_to_lockdown.request,
            handler=lambda _: GoingToLockdown.transition_to_existing_mission_and_report_to_api(),
        ),
    ]
    return State(
        state_name=States.GoingToRecharging,
        signal_exit_event=events.signal_state_machine_exit,
        event_handler_mappings=event_handlers,
    )


def transition_and_start_return_home() -> Transition:
    def _transition(events: Events) -> State:

        events.action_requests.execute_mission.trigger_request(ReturnHomeMission())
        return GoingToRecharging(events)

    return _transition


def transition_to_existing_mission() -> Transition:
    return GoingToRecharging
