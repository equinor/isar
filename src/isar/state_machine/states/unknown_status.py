from typing import TYPE_CHECKING, Callable, List, Optional

from isar.apis.models.models import MaintenanceResponse
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from isar.state_machine.utils.common_event_handlers import stop_mission_event_handler
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class UnknownStatus(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events
        shared_state = state_machine.shared_state

        def _set_maintenance_mode_event_handler(event: Event[bool]):
            should_set_maintenande_mode: bool = event.consume_event()
            if should_set_maintenande_mode:
                events.api_requests.set_maintenance_mode.response.trigger_event(
                    MaintenanceResponse(is_maintenance_mode=True)
                )
                return state_machine.set_maintenance_mode  # type: ignore
            return None

        def _robot_status_event_handler(
            status_changed_event: Event[bool],
        ) -> Optional[Callable]:
            has_changed = status_changed_event.consume_event()
            if not has_changed:
                return None
            robot_status: Optional[RobotStatus] = shared_state.robot_status.check()

            if robot_status == RobotStatus.Home:
                return state_machine.robot_status_home  # type: ignore
            elif robot_status == RobotStatus.Available:
                return state_machine.robot_status_available  # type: ignore
            elif robot_status == RobotStatus.Offline:
                return state_machine.robot_status_offline  # type: ignore
            elif robot_status == RobotStatus.BlockedProtectiveStop:
                return state_machine.robot_status_blocked_protective_stop  # type: ignore
            elif robot_status == RobotStatus.Busy:
                return state_machine.robot_status_busy  # type: ignore
            return None

        def _reset_status_check():
            # Ensures that we will check the status immediately instead of waiting for it to change
            self.events.robot_service_events.robot_status_changed.trigger_event(True)

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="stop_mission_event",
                event=events.api_requests.stop_mission.request,
                handler=lambda event: stop_mission_event_handler(state_machine, event),
            ),
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
            state_name="unknown_status",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
            on_entry=_reset_status_check,
        )
