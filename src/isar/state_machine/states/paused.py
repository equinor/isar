from typing import TYPE_CHECKING, Callable, List, Optional

from isar.config.settings import settings
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from isar.state_machine.utils.common_event_handlers import stop_mission_event_handler

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Paused(EventHandlerBase):

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

            state_machine.publish_mission_aborted(
                "Robot battery too low to continue mission", True
            )
            state_machine.print_transitions()
            state_machine.logger.warning(
                "Cancelling current mission due to low battery"
            )
            state_machine.events.state_machine_events.stop_mission.trigger_event(True)
            return state_machine.stop  # type: ignore

        def _send_to_lockdown_event_handler(
            event: Event[bool],
        ) -> Optional[Callable]:
            should_lockdown: bool = event.consume_event()
            if not should_lockdown:
                return None

            state_machine.print_transitions()
            state_machine.logger.warning(
                "Cancelling current mission due to robot going to lockdown"
            )
            state_machine.events.state_machine_events.stop_mission.trigger_event(True)
            return state_machine.stop_go_to_lockdown  # type: ignore

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
                name="stop_mission_event",
                event=events.api_requests.stop_mission.request,
                handler=lambda event: stop_mission_event_handler(state_machine, event),
            ),
            EventHandlerMapping(
                name="resume_mission_event",
                event=events.api_requests.resume_mission.request,
                handler=_resume_mission_event_handler,
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
            state_name="paused",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
