from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine

from typing import TYPE_CHECKING

from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus, TaskStatus
from robot_interface.models.mission.task import ReturnToHome

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def start_return_home_mission(state_machine: "StateMachine") -> bool:
    state_machine.start_mission(
        Mission(
            tasks=[ReturnToHome()],
            name="Return Home",
        )
    )
    return True


def set_return_home_status(state_machine: "StateMachine") -> bool:
    state_machine.log_mission_overview(mission=state_machine.current_mission)
    state_machine.current_mission.status = MissionStatus.InProgress

    state_machine.current_task = state_machine.task_selector.next_task()
    state_machine.current_task.status = TaskStatus.InProgress

    return True


def return_home_finished(state_machine: "StateMachine") -> bool:
    state_machine.reset_state_machine()
    return True
