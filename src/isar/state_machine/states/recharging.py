from typing import TYPE_CHECKING, List, Optional

from isar.apis.models.models import LockdownResponse, MaintenanceResponse
from isar.config.settings import settings
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.models.events import Event
from isar.state_machine.states.home import Home
from isar.state_machine.states.lockdown import Lockdown
from isar.state_machine.states.maintenance import Maintenance
from isar.state_machine.states.offline import Offline
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Recharging(State):

    @staticmethod
    def transition() -> Transition["Recharging"]:
        def _transition(state_machine: "StateMachine"):
            return Recharging(state_machine)

        return _transition

    def __init__(self, state_machine: "StateMachine"):
        shared_state = state_machine.shared_state
        events = state_machine.events

        def robot_battery_level_updated_handler(event: Event[float]):
            battery_level: float = event.check()
            if battery_level < settings.ROBOT_BATTERY_RECHARGE_THRESHOLD:
                return None

            return Home.transition()

        def robot_offline_handler(event: Event[RobotStatus]):
            robot_status: Optional[RobotStatus] = event.check()

            if robot_status is None:
                return None

            if robot_status == RobotStatus.Offline:
                self.logger.info(
                    "Got robot status offline while in recharging state. Leaving recharging state."
                )
                return Offline.transition()
            return None

        def _send_to_lockdown_event_handler(event: Event[bool]):
            should_lockdown: bool = event.consume_event()
            if not should_lockdown:
                return None

            events.api_requests.send_to_lockdown.response.trigger_event(
                LockdownResponse(lockdown_started=True)
            )
            return Lockdown.transition()

        def _set_maintenance_mode_event_handler(event: Event[bool]):
            should_set_maintenande_mode: bool = event.consume_event()
            if should_set_maintenande_mode:
                events.api_requests.set_maintenance_mode.response.trigger_event(
                    MaintenanceResponse(is_maintenance_mode=True)
                )
                return Maintenance.transition()
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
            state_name=States.Recharging,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
