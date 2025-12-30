from typing import TYPE_CHECKING, List, Optional, Union

import isar.state_machine.states.blocked_protective_stop as BlockedProtectiveStop
import isar.state_machine.states.home as Home
import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.unknown_status as UnknownStatus
from isar.apis.models.models import MaintenanceResponse
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Offline(State):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events
        shared_state = state_machine.shared_state

        def _set_maintenance_mode_event_handler(
            should_set_maintenande_mode: bool,
        ) -> Transition[Maintenance.Maintenance]:
            events.api_requests.set_maintenance_mode.response.trigger_event(
                MaintenanceResponse(is_maintenance_mode=True)
            )
            return Maintenance.transition()

        def _robot_status_event_handler(
            has_changed: bool,
        ) -> Optional[
            Union[
                Transition[Home.Home],
                Transition[InterventionNeeded.InterventionNeeded],
                Transition[BlockedProtectiveStop.BlockedProtectiveStop],
                Transition[UnknownStatus.UnknownStatus],
            ]
        ]:
            robot_status: Optional[RobotStatus] = shared_state.robot_status.check()
            if robot_status == RobotStatus.Offline:
                return None
            elif robot_status == RobotStatus.Home:
                self.logger.info(
                    "Got robot status home while in offline state. Leaving offline state."
                )
                return Home.transition()
            elif robot_status == RobotStatus.Available:
                self.logger.info(
                    "Got robot status available while in offline state. Leaving offline state."
                )
                return InterventionNeeded.transition()
            elif robot_status == RobotStatus.BlockedProtectiveStop:
                self.logger.info(
                    "Got robot status blocked protective stop while in offline state. Leaving offline state."
                )
                return BlockedProtectiveStop.transition()
            self.logger.info(
                f"Got unexpected status {robot_status} while in offline state. Leaving offline state."
            )
            return UnknownStatus.transition()

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="robot_status_event",
                event=events.robot_service_events.robot_status_changed,
                handler=_robot_status_event_handler,
            ),
            EventHandlerMapping(
                name="set_maintenance_mode",
                event=events.api_requests.set_maintenance_mode.request,
                handler=_set_maintenance_mode_event_handler,
            ),
        ]
        super().__init__(
            state_name=States.Offline,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition() -> Transition[Offline]:
    def _transition(state_machine: "StateMachine"):
        return Offline(state_machine)

    return _transition
