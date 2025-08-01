from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine

from robot_interface.models.mission.status import MissionStatus, TaskStatus


def report_failed_mission_and_finalize(state_machine: "StateMachine") -> None:
    state_machine.current_task.status = TaskStatus.Failed
    state_machine.current_mission.status = MissionStatus.Failed
    state_machine.publish_task_status(task=state_machine.current_task)
    state_machine._finalize()


def report_failed_return_home_and_intervention_needed(
    state_machine: "StateMachine",
) -> None:
    error_message: str = "Return home failed."
    state_machine.publish_intervention_needed(error_message=error_message)
