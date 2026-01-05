from typing import TYPE_CHECKING, List, Optional, Union

import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.blocked_protective_stop as BlockedProtectiveStop
import isar.state_machine.states.lockdown as Lockdown
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.offline as Offline
import isar.state_machine.states.recharging as Recharging
import isar.state_machine.states.unknown_status as UnknownStatus
from isar.apis.models.models import LockdownResponse, MaintenanceResponse
from isar.config.settings import settings
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from isar.state_machine.utils.common_event_handlers import (
    return_home_event_handler,
    start_mission_event_handler,
    stop_mission_event_handler,
)
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Home(State):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events
        shared_state = state_machine.shared_state

        # This clears the current robot status value, so we don't read an outdated value
        events.robot_service_events.robot_status_changed.clear_event()

        def _send_to_lockdown_event_handler(
            should_send_robot_home: bool,
        ) -> Transition[Lockdown.Lockdown]:
            events.api_requests.send_to_lockdown.response.trigger_event(
                LockdownResponse(lockdown_started=True)
            )
            return Lockdown.transition()

        def _set_maintenance_mode_event_handler(
            should_set_maintenande_mode: bool,
        ) -> Optional[Transition[Maintenance.Maintenance]]:
            events.api_requests.set_maintenance_mode.response.trigger_event(
                MaintenanceResponse(is_maintenance_mode=True)
            )
            return Maintenance.transition()

        def _robot_status_event_handler(
            has_changed: bool,
        ) -> Optional[
            Union[
                Transition[AwaitNextMission.AwaitNextMission],
                Transition[Offline.Offline],
                Transition[BlockedProtectiveStop.BlockedProtectiveStop],
                Transition[UnknownStatus.UnknownStatus],
            ]
        ]:
            robot_status: Optional[RobotStatus] = shared_state.robot_status.check()
            if robot_status == RobotStatus.Home:
                return None
            elif robot_status == RobotStatus.Available:
                self.logger.info(
                    "Got robot status available while in home state. Leaving home state."
                )
                return AwaitNextMission.transition()
            elif robot_status == RobotStatus.Offline:
                self.logger.info(
                    "Got robot status offline while in home state. Leaving home state."
                )
                return Offline.transition()
            elif robot_status == RobotStatus.BlockedProtectiveStop:
                self.logger.info(
                    "Got robot status blocked protective stop while in home state. Leaving home state."
                )
                return BlockedProtectiveStop.transition()
            self.logger.info(
                f"Got unexpected status {robot_status} while in home state. Leaving home state."
            )
            return UnknownStatus.transition()

        def _robot_battery_level_updated_handler(
            battery_level: float,
        ) -> Optional[Transition[Recharging.Recharging]]:
            if (
                battery_level is None
                or battery_level >= settings.ROBOT_MISSION_BATTERY_START_THRESHOLD
            ):
                return None

            return Recharging.transition()

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
                event=events.api_requests.stop_mission.request,
                handler=lambda event: stop_mission_event_handler(
                    state_machine, event, None
                ),
            ),
            EventHandlerMapping(
                name="robot_status_event",
                event=events.robot_service_events.robot_status_changed,
                handler=_robot_status_event_handler,
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
        super().__init__(
            state_name=States.Home,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition() -> Transition["Home"]:
    def _transition(state_machine: "StateMachine"):
        return Home(state_machine)

    return _transition
