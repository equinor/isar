from typing import List

import isar.state_machine.states.going_to_lockdown as GoingToLockdown
import isar.state_machine.states.resuming_return_home as ResumingReturnHome
import isar.state_machine.states.returning_home as ReturningHome
import isar.state_machine.states.stopping_due_to_maintenance as StoppingDueToMaintenance
import isar.state_machine.states.stopping_paused_return_home as StoppingPausedReturnHome
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.mission.mission import Mission


class ReturnHomePaused(State):

    def __init__(self, events: Events):

        def _send_to_lockdown_event_handler(
            should_lockdown: EmptyMessage,
        ) -> Transition[GoingToLockdown.GoingToLockdown]:
            events.state_machine_events.resume_mission.trigger_event(EmptyMessage())

            return GoingToLockdown.transition_to_existing_mission_and_report_to_api()

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[EmptyMessage](
                name="resume_return_home_event",
                event=events.api_requests.resume_mission.request,
                handler=lambda _: ResumingReturnHome.transition_and_resume_mission_and_reply_to_API(),
            ),
            EventHandlerMapping[EmptyMessage](
                name="robot_battery_below_threshold_event",
                event=events.robot_service_events.battery_below_mission_threshold,
                handler=lambda _: ReturningHome.transition_to_existing_mission(),
            ),
            EventHandlerMapping[Mission](
                name="start_mission_event",
                event=events.api_requests.start_mission.request,
                handler=lambda mission: StoppingPausedReturnHome.transition_and_stop_return_home_and_reply_to_API(
                    mission
                ),
            ),
            EventHandlerMapping[EmptyMessage](
                name="send_to_lockdown_event",
                event=events.api_requests.send_to_lockdown.request,
                handler=_send_to_lockdown_event_handler,
            ),
            EventHandlerMapping[EmptyMessage](
                name="set_maintenance_mode",
                event=events.api_requests.set_maintenance_mode.request,
                handler=lambda _: StoppingDueToMaintenance.transition_and_stop_mission(),
            ),
        ]
        super().__init__(
            state_name=States.ReturnHomePaused,
            signal_exit_event=events.signal_state_machine_exit,
            event_handler_mappings=event_handlers,
        )


def transition() -> Transition[ReturnHomePaused]:
    def _transition(events: Events) -> ReturnHomePaused:
        return ReturnHomePaused(events)

    return _transition
