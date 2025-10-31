from typing import TYPE_CHECKING, Callable, List, Optional

from isar.apis.models.models import LockdownResponse, MaintenanceResponse
from isar.config.settings import settings
from isar.eventhandlers.eventhandler import (
    EventHandlerBase,
    EventHandlerMapping,
    TimeoutHandlerMapping,
)
from isar.models.events import Event
from isar.state_machine.utils.common_event_handlers import (
    return_home_event_handler,
    start_mission_event_handler,
    stop_mission_event_handler,
)

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class AwaitNextMission(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events
        shared_state = state_machine.shared_state

        def _send_to_lockdown_event_handler(
            event: Event[bool],
        ) -> Optional[Callable]:
            should_lockdown: bool = event.consume_event()
            if not should_lockdown:
                return None

            events.api_requests.send_to_lockdown.response.trigger_event(
                LockdownResponse(lockdown_started=True)
            )
            return state_machine.request_lockdown_mission  # type: ignore

        def _robot_battery_level_updated_handler(
            event: Event[float],
        ) -> Optional[Callable]:
            battery_level: float = event.check()
            if (
                battery_level is None
                or battery_level >= settings.ROBOT_MISSION_BATTERY_START_THRESHOLD
            ):
                return None

            return state_machine.request_recharging_mission  # type: ignore

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
                handler=lambda event: stop_mission_event_handler(state_machine, event),
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
                handler=lambda: state_machine.request_return_home,  # type: ignore
            )
        ]

        super().__init__(
            state_name="await_next_mission",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
            timers=timers,
        )
