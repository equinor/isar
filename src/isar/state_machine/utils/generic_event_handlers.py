from enum import Enum
from queue import Queue
from typing import TYPE_CHECKING, Callable, Optional

from isar.models.communication.message import StartMissionMessage
from isar.models.communication.queues.events import Event
from isar.models.communication.queues.queue_utils import (
    check_for_event,
    check_shared_state,
)
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class IdleStates(str, Enum):
    AwaitNextMission = "awaitNextMission"
    Home = "home"
    RobotStandingStill = "robotStandingStill"


def check_and_handle_start_mission_event(
    state_machine: "StateMachine", event: Event[StartMissionMessage]
) -> Optional[Callable]:
    start_mission: Optional[StartMissionMessage] = check_for_event(event)
    if start_mission:
        state_machine.start_mission(mission=start_mission.mission)
        return state_machine.request_mission_start  # type: ignore
    return None


def check_and_handle_return_home_event(
    state_machine: "StateMachine", event: Event[bool]
) -> Optional[Callable]:
    if check_for_event(event):
        state_machine.events.api_requests.return_home.output.put(True)
        return state_machine.request_return_home  # type: ignore
    return None


def check_and_handle_robot_status_event(
    state_machine: "StateMachine",
    expected_status: RobotStatus,
    event: Event[RobotStatus],
) -> Optional[Callable]:
    robot_status: RobotStatus = check_shared_state(event)
    if robot_status != expected_status:
        return state_machine.robot_status_changed  # type: ignore
    return None


def check_and_handle_stop_mission_event(
    state_machine: "StateMachine", event: Queue
) -> Optional[Callable]:
    if check_for_event(event) is not None:
        return state_machine.stop  # type: ignore
    return None
