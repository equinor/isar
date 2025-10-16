from typing import TYPE_CHECKING, Callable, List, Optional

from isar.apis.models.models import LockdownResponse
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from isar.state_machine.utils.common_event_handlers import (
    return_home_event_handler,
    start_mission_event_handler,
    stop_mission_event_handler,
)
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Home(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events
        shared_state = state_machine.shared_state

        def _send_to_lockdown_event_handler(event: Event[bool]):
            should_send_robot_home: bool = event.consume_event()
            if not should_send_robot_home:
                return None

            events.api_requests.send_to_lockdown.response.trigger_event(
                LockdownResponse(lockdown_started=True)
            )
            return state_machine.reached_lockdown  # type: ignore

        def _robot_status_event_handler(
            status_changed_event: Event[bool],
        ) -> Optional[Callable]:
            has_changed = status_changed_event.consume_event()
            if not has_changed:
                return None
            robot_status: Optional[RobotStatus] = shared_state.robot_status.check()
            if not (
                robot_status == RobotStatus.Available
                or robot_status == RobotStatus.Home
            ):
                return state_machine.robot_status_changed  # type: ignore
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
                name="robot_status_event",
                event=events.robot_service_events.robot_status_changed,
                handler=_robot_status_event_handler,
            ),
            EventHandlerMapping(
                name="send_to_lockdown_event",
                event=events.api_requests.send_to_lockdown.request,
                handler=_send_to_lockdown_event_handler,
            ),
        ]
        super().__init__(
            state_name="home",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
