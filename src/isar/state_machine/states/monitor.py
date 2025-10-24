from typing import TYPE_CHECKING, Callable, List, Optional

from isar.config.settings import settings
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from isar.state_machine.utils.common_event_handlers import (
    mission_failed_event_handler,
    mission_started_event_handler,
    stop_mission_event_handler,
)
from robot_interface.models.mission.status import MissionStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Monitor(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events
        shared_state = state_machine.shared_state

        def _pause_mission_event_handler(event: Event[bool]) -> Optional[Callable]:
            if not event.consume_event():
                return None

            return state_machine.pause  # type: ignore

        def _robot_battery_level_updated_handler(
            event: Event[float],
        ) -> Optional[Callable]:
            battery_level: float = event.check()
            if (
                battery_level is None
                or battery_level >= settings.ROBOT_MISSION_BATTERY_START_THRESHOLD
            ):
                return None

            state_machine.logger.warning(
                "Cancelling current mission due to low battery"
            )
            return state_machine.stop_go_to_recharge  # type: ignore

        def _send_to_lockdown_event_handler(
            event: Event[bool],
        ) -> Optional[Callable]:
            should_lockdown: bool = event.consume_event()
            if not should_lockdown:
                return None

            state_machine.logger.warning(
                "Cancelling current mission due to robot going to lockdown"
            )
            return state_machine.stop_go_to_lockdown  # type: ignore

        def _mission_status_event_handler(
            event: Event[MissionStatus],
        ) -> Optional[Callable]:
            mission_status: Optional[MissionStatus] = event.consume_event()
            if mission_status:
                if mission_status not in [
                    MissionStatus.InProgress,
                    MissionStatus.NotStarted,
                    MissionStatus.Paused,
                ]:
                    state_machine.logger.info(
                        f"Mission completed with status {mission_status}"
                    )
                    return state_machine.mission_finished  # type: ignore
            return None

        def _set_maintenance_mode_event_handler(event: Event[bool]):
            should_set_maintenande_mode: bool = event.consume_event()
            if should_set_maintenande_mode:
                state_machine.logger.warning(
                    "Cancelling current mission due to robot going to maintenance mode"
                )
                return state_machine.stop_due_to_maintenance  # type: ignore
            return None

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="stop_mission_event",
                event=events.api_requests.stop_mission.request,
                handler=lambda event: stop_mission_event_handler(state_machine, event),
            ),
            EventHandlerMapping(
                name="pause_mission_event",
                event=events.api_requests.pause_mission.request,
                handler=_pause_mission_event_handler,
            ),
            EventHandlerMapping(
                name="mission_started_event",
                event=events.robot_service_events.mission_started,
                handler=lambda event: mission_started_event_handler(
                    state_machine, event
                ),
            ),
            EventHandlerMapping(
                name="mission_failed_event",
                event=events.robot_service_events.mission_failed,
                handler=lambda event: mission_failed_event_handler(
                    state_machine, event
                ),
            ),
            EventHandlerMapping(
                name="mission_status_event",
                event=events.robot_service_events.mission_status_updated,
                handler=_mission_status_event_handler,
            ),
            EventHandlerMapping(
                name="robot_battery_update_event",
                event=shared_state.robot_battery_level,
                handler=_robot_battery_level_updated_handler,
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
            state_name="monitor",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
