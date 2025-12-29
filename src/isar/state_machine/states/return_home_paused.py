from typing import TYPE_CHECKING, List, Optional

import isar.state_machine.states.going_to_lockdown as GoingToLockdown
import isar.state_machine.states.returning_home as ReturningHome
import isar.state_machine.states.stopping_due_to_maintenance as StoppingDueToMaintenance
import isar.state_machine.states.stopping_paused_return_home as StoppingPausedReturnHome
from isar.apis.models.models import (
    ControlMissionResponse,
    LockdownResponse,
    MissionStartResponse,
)
from isar.config.settings import settings
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.models.events import Event
from isar.state_machine.states_enum import States
from robot_interface.models.mission.mission import Mission

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class ReturnHomePaused(State):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events
        shared_state = state_machine.shared_state

        def _robot_battery_level_updated_handler(
            event: Event[float],
        ) -> Optional[Transition[ReturningHome.ReturningHome]]:
            battery_level: float = event.check()

            if (
                battery_level is None
                or battery_level >= settings.ROBOT_MISSION_BATTERY_START_THRESHOLD
            ):
                return None

            state_machine.events.state_machine_events.resume_mission.trigger_event(True)
            return ReturningHome.transition()

        def _start_mission_event_handler(
            event: Event[Mission],
        ) -> Optional[Transition[StoppingPausedReturnHome.StoppingPausedReturnHome]]:
            mission = event.consume_event()
            if not mission:
                return None

            if not state_machine.battery_level_is_above_mission_start_threshold():
                response = MissionStartResponse(
                    mission_id=None,
                    mission_started=False,
                    mission_not_started_reason="Robot battery too low",
                )
                state_machine.events.api_requests.start_mission.response.trigger_event(
                    response
                )
                return None
            state_machine.events.state_machine_events.stop_mission.trigger_event(True)
            return StoppingPausedReturnHome.transition(mission)

        def _send_to_lockdown_event_handler(
            event: Event[bool],
        ) -> Optional[Transition[GoingToLockdown.GoingToLockdown]]:
            should_lockdown: bool = event.consume_event()
            if not should_lockdown:
                return None

            events.api_requests.send_to_lockdown.response.trigger_event(
                LockdownResponse(lockdown_started=True)
            )
            state_machine.events.state_machine_events.resume_mission.trigger_event(True)

            return GoingToLockdown.transition()

        def _set_maintenance_mode_event_handler(
            event: Event[bool],
        ) -> Optional[Transition[StoppingDueToMaintenance.StoppingDueToMaintenance]]:
            should_set_maintenande_mode: bool = event.consume_event()
            if should_set_maintenande_mode:
                state_machine.logger.warning(
                    "Cancelling current mission due to robot going to maintenance mode"
                )
                state_machine.events.state_machine_events.stop_mission.trigger_event(
                    True
                )
                return StoppingDueToMaintenance.transition("")
            return None

        def _resume_mission_event_handler(
            event: Event[bool],
        ) -> Optional[Transition[ReturningHome.ReturningHome]]:
            if event.consume_event():
                state_machine.events.api_requests.resume_mission.response.trigger_event(
                    ControlMissionResponse(success=True)
                )
                state_machine.events.state_machine_events.resume_mission.trigger_event(
                    True
                )
                return ReturningHome.transition()
            return None

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="resume_return_home_event",
                event=events.api_requests.resume_mission.request,
                handler=_resume_mission_event_handler,
            ),
            EventHandlerMapping(
                name="robot_battery_update_event",
                event=shared_state.robot_battery_level,
                handler=_robot_battery_level_updated_handler,
            ),
            EventHandlerMapping(
                name="start_mission_event",
                event=events.api_requests.start_mission.request,
                handler=_start_mission_event_handler,
            ),
            EventHandlerMapping(
                name="send_to_lockdown_event",
                event=events.api_requests.send_to_lockdown.request,
                handler=_send_to_lockdown_event_handler,
            ),
            EventHandlerMapping(
                name="set_maintenance_mode",
                event=events.api_requests.set_maintenance_mode.request,
                handler=_set_maintenance_mode_event_handler,
            ),
        ]
        super().__init__(
            state_name=States.ReturnHomePaused,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition() -> Transition[ReturnHomePaused]:
    def _transition(state_machine: "StateMachine"):
        return ReturnHomePaused(state_machine)

    return _transition
