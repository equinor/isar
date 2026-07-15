from typing import List

import isar.state_machine.states.going_to_lockdown as GoingToLockdown
import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.recharging as Recharging
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.mission import ReturnHomeMission


class GoingToRecharging(State):

    def __init__(self, events: Events):

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[ErrorMessage](
                name="mission_failed_event",
                event=events.robot_service_events.mission_failed,
                handler=lambda _: InterventionNeeded.transition(
                    "Return home to recharge failed"
                ),
            ),
            EventHandlerMapping[EmptyMessage](
                name="mission_succeeded_event",
                event=events.robot_service_events.mission_succeeded,
                handler=lambda _: Recharging.transition(),
            ),
            EventHandlerMapping[EmptyMessage](
                name="send_to_lockdown_event",
                event=events.api_requests.send_to_lockdown.request,
                handler=lambda _: GoingToLockdown.transition_to_existing_mission_and_report_to_api(),
            ),
        ]
        super().__init__(
            state_name=States.GoingToRecharging,
            signal_exit_event=events.signal_state_machine_exit,
            event_handler_mappings=event_handlers,
        )


def transition_and_start_return_home() -> Transition[GoingToRecharging]:
    def _transition(events: Events) -> GoingToRecharging:
        events.robot_service_events.mission_failed.clear_event()
        events.robot_service_events.mission_succeeded.clear_event()

        events.state_machine_events.start_mission.trigger_event(ReturnHomeMission())
        return GoingToRecharging(events)

    return _transition


def transition_to_existing_mission() -> Transition[GoingToRecharging]:
    def _transition(events: Events) -> GoingToRecharging:
        return GoingToRecharging(events)

    return _transition
