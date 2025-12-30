from typing import TYPE_CHECKING, List, Optional

import isar.state_machine.states.going_to_lockdown as GoingToLockdown
import isar.state_machine.states.going_to_recharging as GoingToRecharging
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.returning_home as ReturningHome
from isar.apis.models.models import LockdownResponse, MaintenanceResponse
from isar.config.settings import settings
from isar.eventhandlers.eventhandler import (
    EventHandlerMapping,
    State,
    TimeoutHandlerMapping,
    Transition,
)
from isar.state_machine.states_enum import States
from isar.state_machine.utils.common_event_handlers import (
    return_home_event_handler,
    start_mission_event_handler,
    stop_mission_event_handler,
)

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class AwaitNextMission(State):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events
        shared_state = state_machine.shared_state

        def _send_to_lockdown_event_handler(
            should_lockdown: bool,
        ) -> Transition[GoingToLockdown.GoingToLockdown]:
            events.api_requests.send_to_lockdown.response.trigger_event(
                LockdownResponse(lockdown_started=True)
            )

            state_machine.start_return_home_mission()
            return GoingToLockdown.transition()

        def _robot_battery_level_updated_handler(
            battery_level: float,
        ) -> Optional[Transition[GoingToRecharging.GoingToRecharging]]:
            if (
                battery_level is None
                or battery_level >= settings.ROBOT_MISSION_BATTERY_START_THRESHOLD
            ):
                return None

            state_machine.start_return_home_mission()
            return GoingToRecharging.transition()

        def _set_maintenance_mode_event_handler(
            should_set_maintenande_mode: bool,
        ) -> Transition[Maintenance.Maintenance]:
            events.api_requests.set_maintenance_mode.response.trigger_event(
                MaintenanceResponse(is_maintenance_mode=True)
            )
            return Maintenance.transition()

        def _start_return_home() -> Transition[ReturningHome.ReturningHome]:
            state_machine.start_return_home_mission()
            return ReturningHome.transition()

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="start_mission_event",
                event=events.api_requests.start_mission.request,
                handler=lambda event: start_mission_event_handler(
                    state_machine, event, events.api_requests.start_mission.response
                ),
            ),
            EventHandlerMapping(
                name="return_home_event",
                event=events.api_requests.return_home.request,
                handler=lambda event: return_home_event_handler(state_machine, event),
            ),
            EventHandlerMapping(
                name="stop_mission_event",
                event=events.api_requests.return_home.request,
                handler=lambda event: stop_mission_event_handler(
                    state_machine, event, None
                ),
            ),
            EventHandlerMapping(
                name="send_to_lockdown_event",
                event=events.api_requests.send_to_lockdown.request,
                handler=_send_to_lockdown_event_handler,
            ),
            EventHandlerMapping(
                name="robot_battery_update_event",
                event=shared_state.robot_battery_level,
                handler=_robot_battery_level_updated_handler,
                should_not_consume=True,
            ),
            EventHandlerMapping(
                name="set_maintenance_mode",
                event=events.api_requests.set_maintenance_mode.request,
                handler=_set_maintenance_mode_event_handler,
            ),
        ]

        timers: List[TimeoutHandlerMapping] = [
            TimeoutHandlerMapping(
                name="should_return_home_timer",
                timeout_in_seconds=settings.RETURN_HOME_DELAY,
                handler=_start_return_home,
            )
        ]

        super().__init__(
            state_name=States.AwaitNextMission,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
            timers=timers,
        )


def transition() -> Transition[AwaitNextMission]:
    def _transition(state_machine: "StateMachine"):
        return AwaitNextMission(state_machine)

    return _transition
