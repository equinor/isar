from typing import TYPE_CHECKING, List, Optional

from isar.apis.models.models import LockdownResponse, MaintenanceResponse
from isar.config.settings import settings
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Recharging(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        shared_state = state_machine.shared_state
        events = state_machine.events

        def robot_battery_level_updated_handler(event: Event[float]):
            battery_level: float = event.check()
            if battery_level < settings.ROBOT_BATTERY_RECHARGE_THRESHOLD:
                return None

            return state_machine.robot_recharged  # type: ignore

        def robot_offline_handler(event: Event[RobotStatus]):
            robot_status: Optional[RobotStatus] = event.check()

            if robot_status is None:
                return None

            if robot_status == RobotStatus.Offline:
                return state_machine.robot_went_offline  # type: ignore

        def _send_to_lockdown_event_handler(event: Event[bool]):
            should_lockdown: bool = event.consume_event()
            if not should_lockdown:
                return None

            events.api_requests.send_to_lockdown.response.trigger_event(
                LockdownResponse(lockdown_started=True)
            )
            return state_machine.reached_lockdown  # type: ignore

        def _set_maintenance_mode_event_handler(event: Event[bool]):
            should_set_maintenande_mode: bool = event.consume_event()
            if should_set_maintenande_mode:
                events.api_requests.set_maintenance_mode.response.trigger_event(
                    MaintenanceResponse(is_maintenance_mode=True)
                )
                return state_machine.set_maintenance_mode  # type: ignore
            return None

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="robot_battery_update_event",
                event=shared_state.robot_battery_level,
                handler=robot_battery_level_updated_handler,
            ),
            EventHandlerMapping(
                name="robot_offline_event",
                event=shared_state.robot_status,
                handler=robot_offline_handler,
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
            state_name="recharging",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
