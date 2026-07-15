from typing import List

import isar.state_machine.states.going_to_lockdown as GoingToLockdown
import isar.state_machine.states.monitor as Monitor
from isar.apis.models.models import LockdownResponse
from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.services.utilities.mqtt_utilities import publish_mission_aborted
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States


class StoppingGoToLockdown(State):

    def __init__(self, events: Events, mission_id: str):

        def _failed_stop_event_handler(
            empty_event: EmptyMessage,
        ) -> Transition[Monitor.Monitor]:
            events.api_requests.send_to_lockdown.response.trigger_event(
                LockdownResponse(
                    lockdown_started=False,
                    failure_reason="Failed to stop ongoing mission",
                )
            )
            return Monitor.transition_with_existing_mission(mission_id)

        def _successful_stop_event_handler(
            successful_stop: AbortedMission | EmptyMessage,
        ) -> Transition[GoingToLockdown.GoingToLockdown]:
            publish_mission_aborted(
                events.mqtt_queue, mission_id, "Robot being sent to lockdown"
            )
            return GoingToLockdown.transition_and_start_mission_and_report_to_api()

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[EmptyMessage](
                name="failed_stop_event",
                event=events.robot_service_events.mission_failed_to_stop,
                handler=_failed_stop_event_handler,
            ),
            EventHandlerMapping[AbortedMission](
                name="successful_stop_event",
                event=events.robot_service_events.mission_successfully_stopped,
                handler=_successful_stop_event_handler,
            ),
            EventHandlerMapping[EmptyMessage](
                name="mission_already_done_event",
                event=events.robot_service_events.stopped_mission_already_done,
                handler=_successful_stop_event_handler,
            ),
        ]
        super().__init__(
            state_name=States.StoppingGoToLockdown,
            signal_exit_event=events.signal_state_machine_exit,
            event_handler_mappings=event_handlers,
        )


def transition_and_stop_mission(mission_id: str) -> Transition[StoppingGoToLockdown]:
    def _transition(events: Events) -> StoppingGoToLockdown:
        events.state_machine_events.stop_mission.trigger_event(EmptyMessage())
        return StoppingGoToLockdown(events, mission_id)

    return _transition
