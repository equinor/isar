from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine

from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.status import MissionStatus, TaskStatus


def finish_mission(state_machine: "StateMachine") -> bool:
    fail_statuses: List[TaskStatus] = [
        TaskStatus.Cancelled,
        TaskStatus.Failed,
    ]
    partially_fail_statuses = fail_statuses + [TaskStatus.PartiallySuccessful]

    if len(state_machine.current_mission.tasks) == 0:
        state_machine.current_mission.status = MissionStatus.Successful
    elif all(
        task.status in fail_statuses for task in state_machine.current_mission.tasks
    ):
        state_machine.current_mission.error_message = ErrorMessage(
            error_reason=None,
            error_description="The mission failed because all tasks in the mission "
            "failed",
        )
        state_machine.current_mission.status = MissionStatus.Failed
    elif any(
        task.status in partially_fail_statuses
        for task in state_machine.current_mission.tasks
    ):
        state_machine.current_mission.status = MissionStatus.PartiallySuccessful
    else:
        state_machine.current_mission.status = MissionStatus.Successful
    state_machine._finalize()

    state_machine.current_task = None
    state_machine.send_task_status()
    return True
