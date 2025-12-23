from typing import TYPE_CHECKING, List, Optional, Union

from isar.apis.models.models import MaintenanceResponse
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.models.events import Event
from isar.state_machine.states.home import Home
from isar.state_machine.states.intervention_needed import InterventionNeeded
from isar.state_machine.states.maintenance import Maintenance
from isar.state_machine.states.offline import Offline
from isar.state_machine.states.unknown_status import UnknownStatus
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class BlockedProtectiveStop(State):

    @staticmethod
    def transition() -> Transition["BlockedProtectiveStop"]:
        def _transition(state_machine: "StateMachine"):
            return BlockedProtectiveStop(state_machine)

        return _transition

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events
        shared_state = state_machine.shared_state

        def _set_maintenance_mode_event_handler(
            event: Event[bool],
        ) -> Optional[Transition[Maintenance]]:
            should_set_maintenande_mode: bool = event.consume_event()
            if should_set_maintenande_mode:
                events.api_requests.set_maintenance_mode.response.trigger_event(
                    MaintenanceResponse(is_maintenance_mode=True)
                )
                return Maintenance.transition()
            return None

        def _robot_status_event_handler(
            status_changed_event: Event[bool],
        ) -> Optional[
            Union[
                Transition[Home],
                Transition[InterventionNeeded],
                Transition[Offline],
                Transition[UnknownStatus],
            ]
        ]:
            has_changed = status_changed_event.consume_event()
            if not has_changed:
                return None
            robot_status: Optional[RobotStatus] = shared_state.robot_status.check()
            if robot_status == RobotStatus.BlockedProtectiveStop:
                return None
            elif robot_status == RobotStatus.Home:
                self.logger.info(
                    "Got robot status home while in blocked protective stop state. Leaving blocked protective stop state."
                )
                return Home.transition()
            elif robot_status == RobotStatus.Available:
                self.logger.info(
                    "Got robot status available while in blocked protective stop state. Leaving blocked protective stop state."
                )
                return InterventionNeeded.transition()
            elif robot_status == RobotStatus.Offline:
                self.logger.info(
                    "Got robot status offline while in blocked protective stop state. Leaving blocked protective stop state."
                )
                return Offline.transition()
            self.logger.info(
                f"Got unexpected status {robot_status} while in blocked protective stop state. Leaving blocked protective stop state."
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
            state_name=States.BlockedProtectiveStop,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
