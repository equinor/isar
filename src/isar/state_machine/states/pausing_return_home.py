from typing import TYPE_CHECKING, Callable, List, Optional

from isar.apis.models.models import ControlMissionResponse
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.status import MissionStatus, TaskStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class PausingReturnHome(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

        def _failed_pause_event_handler(
            event: Event[ErrorMessage],
        ) -> Optional[Callable]:
            error_message: Optional[ErrorMessage] = event.consume_event()

            paused_mission_response: ControlMissionResponse = (
                state_machine._make_control_mission_response()
            )

            state_machine.events.api_requests.pause_mission.response.trigger_event(
                paused_mission_response
            )

            state_machine.publish_mission_status()
            state_machine.send_task_status()

            if error_message is not None:
                return state_machine.return_home_mission_pausing_failed  # type: ignore
            return None

        def _successful_pause_event_handler(event: Event[bool]) -> Optional[Callable]:
            if event.consume_event():

                state_machine.current_mission.status = MissionStatus.Paused
                state_machine.current_task.status = TaskStatus.Paused

                paused_mission_response: ControlMissionResponse = (
                    state_machine._make_control_mission_response()
                )

                state_machine.events.api_requests.pause_mission.response.trigger_event(
                    paused_mission_response
                )

                state_machine.publish_mission_status()
                state_machine.send_task_status()

                return state_machine.return_home_mission_paused  # type: ignore
            return None

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="failed_pause_event",
                event=events.robot_service_events.mission_failed_to_pause,
                handler=_failed_pause_event_handler,
            ),
            EventHandlerMapping(
                name="successful_stop_event",
                event=events.robot_service_events.mission_successfully_paused,
                handler=_successful_pause_event_handler,
            ),
        ]
        super().__init__(
            state_name="pausing_return_home",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
