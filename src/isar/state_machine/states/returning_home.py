from typing import List

import isar.state_machine.states.going_to_lockdown as GoingToLockdown
import isar.state_machine.states.going_to_recharging as GoingToRecharging
import isar.state_machine.states.home as Home
import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.pausing_return_home as PausingReturnHome
import isar.state_machine.states.stopping_due_to_maintenance as StoppingDueToMaintenance
import isar.state_machine.states.stopping_return_home as StoppingReturnHome
from isar.config.settings import settings
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.mission import Mission, ReturnHomeMission


class ReturningHome(State):

    def __init__(
        self,
        events: Events,
        retries: int = settings.RETURN_HOME_RETRY_LIMIT - 1,
    ):

        def _mission_failed_event_handler(
            error_message: ErrorMessage,
        ) -> (
            Transition[InterventionNeeded.InterventionNeeded]
            | Transition[ReturningHome]
        ):
            if retries < 1:
                return InterventionNeeded.transition(
                    f"Return home failed after {settings.RETURN_HOME_RETRY_LIMIT} attempts"
                )
            else:
                return transition_and_start_mission(False, retries - 1)

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[EmptyMessage](
                name="pause_mission_event",
                event=events.api_requests.pause_mission.request,
                handler=lambda _: PausingReturnHome.transition_and_pause_mission_and_reply_to_API(),
            ),
            EventHandlerMapping[ErrorMessage](
                name="mission_failed_event",
                event=events.robot_service_events.mission_failed,
                handler=_mission_failed_event_handler,
            ),
            EventHandlerMapping[Mission](
                name="start_mission_event",
                event=events.api_requests.start_mission.request,
                handler=lambda mission: StoppingReturnHome.transition_and_stop_return_home_and_reply_to_API(
                    mission
                ),
            ),
            EventHandlerMapping[EmptyMessage](
                name="mission_succeeded_event",
                event=events.robot_service_events.mission_succeeded,
                handler=lambda _: Home.transition(),
            ),
            EventHandlerMapping[EmptyMessage](
                name="robot_battery_below_threshold_event",
                event=events.robot_service_events.battery_below_mission_threshold,
                handler=lambda _: GoingToRecharging.transition_to_existing_mission(),
            ),
            EventHandlerMapping[EmptyMessage](
                name="send_to_lockdown_event",
                event=events.api_requests.send_to_lockdown.request,
                handler=lambda _: GoingToLockdown.transition_to_existing_mission_and_report_to_api(),
            ),
            EventHandlerMapping[EmptyMessage](
                name="set_maintenance_mode",
                event=events.api_requests.set_maintenance_mode.request,
                handler=lambda _: StoppingDueToMaintenance.transition_and_stop_mission(),
            ),
        ]
        super().__init__(
            state_name=States.ReturningHome,
            signal_exit_event=events.signal_state_machine_exit,
            event_handler_mappings=event_handlers,
        )


def transition_and_start_mission(
    should_respond_to_API_request: bool = False,
    retries: int = settings.RETURN_HOME_RETRY_LIMIT - 1,
) -> Transition[ReturningHome]:
    def _transition(events: Events) -> ReturningHome:
        events.robot_service_events.mission_failed.clear_event()
        events.robot_service_events.mission_succeeded.clear_event()

        events.state_machine_events.start_mission.trigger_event(ReturnHomeMission())

        if should_respond_to_API_request:
            events.api_requests.return_home.response.trigger_event(EmptyMessage())
        return ReturningHome(events, retries=retries)

    return _transition


def transition_to_existing_mission() -> Transition[ReturningHome]:
    def _transition(events: Events) -> ReturningHome:
        return ReturningHome(events)

    return _transition
