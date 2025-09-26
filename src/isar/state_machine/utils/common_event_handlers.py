from typing import TYPE_CHECKING, Callable, Optional

from isar.apis.models.models import ControlMissionResponse, MissionStartResponse
from isar.models.events import Event
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def start_mission_event_handler(
    state_machine: "StateMachine",
    event: Event[Mission],
    response: Event[MissionStartResponse],
) -> Optional[Callable]:
    mission: Optional[Mission] = event.consume_event()
    if mission:
        if not state_machine.battery_level_is_above_mission_start_threshold():
            response.trigger_event(
                MissionStartResponse(
                    mission_id=mission.id,
                    mission_started=False,
                    mission_not_started_reason="Robot battery too low",
                )
            )
            return None
        state_machine.start_mission(mission=mission)
        return state_machine.request_mission_start  # type: ignore
    return None


def return_home_event_handler(
    state_machine: "StateMachine", event: Event[bool]
) -> Optional[Callable]:
    if event.consume_event():
        state_machine.events.api_requests.return_home.response.trigger_event(True)
        return state_machine.request_return_home  # type: ignore
    return None


def robot_status_event_handler(
    state_machine: "StateMachine",
    expected_status: RobotStatus,
    event: Event[RobotStatus],
) -> Optional[Callable]:
    robot_status: RobotStatus = event.check()
    if robot_status != expected_status:
        return state_machine.robot_status_changed  # type: ignore
    return None


def stop_mission_event_handler(
    state_machine: "StateMachine", event: Event[str]
) -> Optional[Callable]:
    mission_id: str = event.consume_event()
    if mission_id is not None:
        if state_machine.current_mission.id == mission_id or mission_id == "":
            return state_machine.stop  # type: ignore
        else:
            state_machine.events.api_requests.stop_mission.response.trigger_event(
                ControlMissionResponse(
                    success=False, failure_reason="Mission not found"
                )
            )
    return None


def mission_started_event_handler(
    state_machine: "StateMachine",
    event: Event[bool],
) -> Optional[Callable]:
    if event.consume_event():
        state_machine.logger.info("Received confirmation that mission has started")
    return None


def mission_failed_event_handler(
    state_machine: "StateMachine",
    event: Event[Optional[ErrorMessage]],
) -> Optional[Callable]:
    mission_failed: Optional[ErrorMessage] = event.consume_event()
    if mission_failed is not None:
        state_machine.logger.warning(
            f"Failed to initiate mission "
            f"{str(state_machine.current_mission.id)[:8]} because: "
            f"{mission_failed.error_description}"
        )
        state_machine.current_mission.error_message = ErrorMessage(
            error_reason=mission_failed.error_reason,
            error_description=mission_failed.error_description,
        )
        return state_machine.mission_failed_to_start  # type: ignore
    return None
