from typing import List

import isar.state_machine.states.going_to_recharging as GoingToRecharging
import isar.state_machine.states.going_to_recharging_with_mission as GoingToRechargingWithMission
import isar.state_machine.states.intervention_needed as InterventionNeeded
from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States


class StoppingGoToRecharge(State):

    def __init__(self, events: Events):

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[EmptyMessage](
                name="failed_stop_event",
                event=events.robot_service_events.mission_failed_to_stop,
                handler=lambda _: InterventionNeeded.transition(
                    "Failed to stop mission when battery was low"
                ),
            ),
            EventHandlerMapping[AbortedMission](
                name="successful_stop_event",
                event=events.robot_service_events.mission_successfully_stopped,
                handler=lambda aborted_mission: GoingToRechargingWithMission.transition_and_start_return_home(
                    aborted_mission
                ),
            ),
            EventHandlerMapping[EmptyMessage](
                name="mission_already_done_event",
                event=events.robot_service_events.stopped_mission_already_done,
                handler=lambda _: GoingToRecharging.transition_and_start_return_home(),
            ),
        ]
        super().__init__(
            state_name=States.StoppingGoToRecharge,
            signal_exit_event=events.signal_state_machine_exit,
            event_handler_mappings=event_handlers,
        )


def transition_and_stop_mission() -> Transition[StoppingGoToRecharge]:
    def _transition(events: Events) -> StoppingGoToRecharge:
        events.state_machine_events.stop_mission.trigger_event(EmptyMessage())
        return StoppingGoToRecharge(events)

    return _transition
