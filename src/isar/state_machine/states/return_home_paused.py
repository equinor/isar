from typing import TYPE_CHECKING, Callable, List, Optional

from isar.apis.models.models import LockdownResponse, MissionStartResponse
from isar.config.settings import settings
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from robot_interface.models.mission.mission import Mission

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class ReturnHomePaused(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events
        shared_state = state_machine.shared_state

        def _robot_battery_level_updated_handler(
            event: Event[float],
        ) -> Optional[Callable]:
            battery_level: float = event.check()

            if (
                battery_level is None
                or battery_level >= settings.ROBOT_MISSION_BATTERY_START_THRESHOLD
            ):
                return None

            state_machine.events.state_machine_events.resume_mission.trigger_event(True)
            return state_machine.resume  # type: ignore

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
            state_machine.events.state_machine_events.stop_mission.trigger_event(True)
            return state_machine.stop_return_home  # type: ignore

        def _send_to_lockdown_event_handler(
            event: Event[bool],
        ) -> Optional[Callable]:
            should_lockdown: bool = event.consume_event()
            if not should_lockdown:
                return None

            events.api_requests.send_to_lockdown.response.trigger_event(
                LockdownResponse(lockdown_started=True)
            )
            state_machine.events.state_machine_events.resume_mission.trigger_event(True)
            return state_machine.resume_lockdown  # type: ignore

        def _set_maintenance_mode_event_handler(event: Event[bool]):
            should_set_maintenande_mode: bool = event.consume_event()
            if should_set_maintenande_mode:
                state_machine.logger.warning(
                    "Cancelling current mission due to robot going to maintenance mode"
                )
                state_machine.events.state_machine_events.stop_mission.trigger_event(
                    True
                )
                return state_machine.stop_due_to_maintenance  # type: ignore
            return None

        def _resume_mission_event_handler(event: Event[bool]):
            if event.consume_event():
                state_machine.events.state_machine_events.resume_mission.trigger_event(
                    True
                )
                return state_machine.resume  # type: ignore
            return None

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="resume_return_home_event",
                event=events.api_requests.resume_mission.request,
                handler=_resume_mission_event_handler,
            ),
            EventHandlerMapping(
                name="robot_battery_update_event",
                event=shared_state.robot_battery_level,
                handler=_robot_battery_level_updated_handler,
            ),
            EventHandlerMapping(
                name="start_mission_event",
                event=events.api_requests.start_mission.request,
                handler=_start_mission_event_handler,
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
            state_name="return_home_paused",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
