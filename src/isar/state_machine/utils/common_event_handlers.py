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
    if not mission:
        return None

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


def return_home_event_handler(
    state_machine: "StateMachine", event: Event[bool]
) -> Optional[Callable]:
    if not event.consume_event():
        return None

    state_machine.events.api_requests.return_home.response.trigger_event(True)
    return state_machine.request_return_home  # type: ignore


def robot_status_event_handler(
    state_machine: "StateMachine",
    expected_status: RobotStatus,
    status_changed_event: Event[bool],
    status_event: Event[RobotStatus],
) -> Optional[Callable]:
    if not status_changed_event.consume_event():
        return None

    robot_status: Optional[RobotStatus] = status_event.check()
    if robot_status != expected_status:
        return state_machine.robot_status_changed  # type: ignore
    return None


def stop_mission_event_handler(
    state_machine: "StateMachine", event: Event[str]
) -> Optional[Callable]:
    mission_id: str = event.consume_event()
    if mission_id is None:
        return None

    if state_machine.shared_state.mission_id.check() == mission_id or mission_id == "":
        return state_machine.stop  # type: ignore
    else:
        state_machine.events.api_requests.stop_mission.response.trigger_event(
            ControlMissionResponse(success=False, failure_reason="Mission not found")
        )
        return None


def mission_started_event_handler(
    state_machine: "StateMachine",
    event: Event[bool],
) -> Optional[Callable]:
    if not event.consume_event():
        return None

    state_machine.logger.info("Received confirmation that mission has started")
    return None


def mission_failed_event_handler(
    state_machine: "StateMachine",
    event: Event[Optional[ErrorMessage]],
) -> Optional[Callable]:
    mission_failed: Optional[ErrorMessage] = event.consume_event()
    if mission_failed is None:
        return None

    state_machine.logger.warning(
        f"Failed to initiate mission because: " f"{mission_failed.error_description}"
    )
    return state_machine.mission_failed_to_start  # type: ignore
