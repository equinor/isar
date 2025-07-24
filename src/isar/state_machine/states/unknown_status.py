from typing import TYPE_CHECKING, Callable, List, Optional

from isar.apis.models.models import ControlMissionResponse
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.communication.queues.events import Event
from isar.models.communication.queues.queue_utils import (
    check_for_event,
    check_shared_state,
)
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def UnknownStatus(state_machine: "StateMachine"):
    events = state_machine.events
    shared_state = state_machine.shared_state

    def _check_and_handle_stop_mission_event(event: Event[str]) -> Optional[Callable]:
        mission_id: str = check_for_event(event)
        if mission_id is not None:
            if state_machine.current_mission.id == mission_id or mission_id == "":
                return state_machine.stop  # type: ignore
            else:
                events.api_requests.stop_mission.output.put(
                    ControlMissionResponse(
                        mission_id=mission_id,
                        mission_status=state_machine.current_mission.status,
                        mission_not_found=True,
                        task_id=state_machine.current_task.id,
                        task_status=state_machine.current_task.status,
                    )
                )
        return None

    def _check_and_handle_robot_status_event(
        event: Event[RobotStatus],
    ) -> Optional[Callable]:
        robot_status: RobotStatus = check_shared_state(event)
        if (
            robot_status == RobotStatus.Home
            or robot_status == RobotStatus.Offline
            or robot_status == RobotStatus.BlockedProtectiveStop
            or robot_status == RobotStatus.Available
        ):
            return state_machine.robot_status_changed  # type: ignore
        return None

    event_handlers: List[EventHandlerMapping] = [
        EventHandlerMapping(
            name="stop_mission_event",
            eventQueue=events.api_requests.stop_mission.input,
            handler=_check_and_handle_stop_mission_event,
        ),
        EventHandlerMapping(
            name="robot_status_event",
            eventQueue=shared_state.robot_status,
            handler=_check_and_handle_robot_status_event,
        ),
    ]
    return EventHandlerBase(
        state_name="unknown_status",
        state_machine=state_machine,
        event_handler_mappings=event_handlers,
    )
