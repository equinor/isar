from typing import List

import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.intervention_needed as InterventionNeeded
from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States


class StoppingUnknownMission(State):

    def __init__(self, events: Events):

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[EmptyMessage](
                name="failed_stop_event",
                event=events.robot_service_events.mission_failed_to_stop,
                handler=lambda _: InterventionNeeded.transition(
                    "Failed to stop unknown mission"
                ),
            ),
            EventHandlerMapping[AbortedMission](
                name="successful_stop_event",
                event=events.robot_service_events.mission_successfully_stopped,
                handler=lambda _: AwaitNextMission.transition(),
            ),
            EventHandlerMapping[EmptyMessage](
                name="mission_already_done_event",
                event=events.robot_service_events.stopped_mission_already_done,
                handler=lambda _: AwaitNextMission.transition(),
            ),
        ]
        super().__init__(
            state_name=States.StoppingUnknownMission,
            signal_exit_event=events.signal_state_machine_exit,
            event_handler_mappings=event_handlers,
        )


def transition() -> Transition[StoppingUnknownMission]:
    def _transition(events: Events) -> StoppingUnknownMission:
        events.state_machine_events.stop_mission.trigger_event(EmptyMessage())
        return StoppingUnknownMission(events)

    return _transition
