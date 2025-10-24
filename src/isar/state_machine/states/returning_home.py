from typing import TYPE_CHECKING, Callable, List, Optional

from isar.apis.models.models import LockdownResponse, MissionStartResponse
from isar.config.settings import settings
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from isar.state_machine.utils.common_event_handlers import mission_started_event_handler
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class ReturningHome(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        self.failed_return_home_attemps: int = 0
        events = state_machine.events
        shared_state = state_machine.shared_state

        def _pause_mission_event_handler(event: Event[bool]) -> Optional[Callable]:
            if not event.consume_event():
                return None

            return state_machine.pause_return_home  # type: ignore

        def _start_mission_event_handler(
            event: Event[Mission],
        ) -> Optional[Callable]:
            if not event.has_event():
                return None

            if not state_machine.battery_level_is_above_mission_start_threshold():
                state_machine.events.api_requests.start_mission.request.consume_event()
                response = MissionStartResponse(
                    mission_id=None,
                    mission_started=False,
                    mission_not_started_reason="Robot battery too low",
                )
                state_machine.events.api_requests.start_mission.response.trigger_event(
                    response
                )
                return None

            return state_machine.stop_return_home  # type: ignore

        def _mission_status_event_handler(
            event: Event[MissionStatus],
        ) -> Optional[Callable]:
            mission_status: Optional[MissionStatus] = event.consume_event()

            if mission_status and mission_status not in [
                MissionStatus.InProgress,
                MissionStatus.NotStarted,
                MissionStatus.Paused,
            ]:
                if mission_status != MissionStatus.Successful:
                    self.failed_return_home_attemps += 1
                    return state_machine.return_home_failed  # type: ignore

                self.failed_return_home_attemps = 0
                return state_machine.returned_home  # type: ignore
            return None

        def _send_to_lockdown_event_handler(
            event: Event[bool],
        ) -> Optional[Callable]:
            should_lockdown: bool = event.consume_event()
            if not should_lockdown:
                return None

            events.api_requests.send_to_lockdown.response.trigger_event(
                LockdownResponse(lockdown_started=True)
            )
            return state_machine.go_to_lockdown  # type: ignore

        def _mission_failed_event_handler(
            event: Event[Optional[ErrorMessage]],
        ) -> Optional[Callable]:
            mission_failed: Optional[ErrorMessage] = event.consume_event()
            if mission_failed is not None:
                state_machine.logger.warning(
                    f"Failed to initiate return home because: "
                    f"{mission_failed.error_description}"
                )
                return state_machine.return_home_failed  # type: ignore
            return None

        def _set_maintenance_mode_event_handler(event: Event[bool]):
            should_set_maintenande_mode: bool = event.consume_event()
            if should_set_maintenande_mode:
                state_machine.logger.warning(
                    "Cancelling current mission due to robot going to maintenance mode"
                )
                return state_machine.stop_due_to_maintenance  # type: ignore
            return None

        def _robot_battery_level_updated_handler(
            event: Event[float],
        ) -> Optional[Callable]:
            battery_level: float = event.check()
            if (
                battery_level is None
                or battery_level >= settings.ROBOT_MISSION_BATTERY_START_THRESHOLD
            ):
                return None

            return state_machine.go_to_recharging  # type: ignore

        event_handlers: List[EventHandlerMapping] = [
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
                handler=_mission_failed_event_handler,
            ),
            EventHandlerMapping(
                name="start_mission_event",
                event=events.api_requests.start_mission.request,
                handler=_start_mission_event_handler,
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
            state_name="returning_home",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
