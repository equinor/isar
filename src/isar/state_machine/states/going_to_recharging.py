import isar.state_machine.states.going_to_lockdown as GoingToLockdown
import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.recharging as Recharging
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import (
    EventHandlerMapping,
    StateDef,
    Transition,
    state_definition,
    transition_definition,
)
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage


@state_definition
def GoingToRecharging(events: Events) -> StateDef:

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[ErrorMessage](
            event=events.action_requests.return_home.failure,
            handler=lambda _: InterventionNeeded.transition(
                events, "Return home to recharge failed"
            ),
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.action_requests.return_home.success,
            handler=lambda _: Recharging.transition(events),
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.send_to_lockdown.request,
            handler=lambda _: GoingToLockdown.transition_to_existing_mission_and_report_to_api(
                events
            ),
        ),
    ]
    return StateDef(
        name=States.GoingToRecharging,
        handlers=event_handlers,
    )


@transition_definition
def transition_and_start_return_home(events: Events) -> Transition:
    def _side_effect(events: Events) -> None:
        events.action_requests.return_home.trigger_request(EmptyMessage())

    return Transition(GoingToRecharging(events), _side_effect)


@transition_definition
def transition_to_existing_mission(events: Events) -> Transition:
    return Transition(GoingToRecharging(events))
