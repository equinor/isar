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
            if battery_level < settings.ROBOT_MISSION_BATTERY_START_THRESHOLD:
                return state_machine.resume  # type: ignore
            return None

        def _start_mission_event_handler(
            event: Event[Mission],
        ) -> Optional[Callable]:
            if event.has_event():
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
            return None

        def _send_to_lockdown_event_handler(
            event: Event[bool],
        ) -> Optional[Callable]:
            should_lockdown: bool = event.consume_event()
            if should_lockdown:
                events.api_requests.send_to_lockdown.response.trigger_event(
                    LockdownResponse(lockdown_started=True)
                )
                return state_machine.resume_lockdown  # type: ignore
            return None

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="resume_return_home_event",
                event=events.api_requests.resume_mission.request,
                handler=lambda event: state_machine.resume if event.consume_event() else None,  # type: ignore
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
        ]
        super().__init__(
            state_name="return_home_paused",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
