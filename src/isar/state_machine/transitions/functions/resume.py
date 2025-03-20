from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine

from isar.apis.models.models import ControlMissionResponse
from robot_interface.models.mission.status import MissionStatus, TaskStatus


def resume_mission(state_machine: "StateMachine") -> bool:
    state_machine.logger.info("Resuming mission: %s", state_machine.current_mission.id)
    state_machine.current_mission.status = MissionStatus.InProgress
    state_machine.current_mission.error_message = None
    state_machine.current_task.status = TaskStatus.InProgress

    state_machine.mission_ongoing = True

    state_machine.publish_mission_status()
    state_machine.publish_task_status(task=state_machine.current_task)

    resume_mission_response: ControlMissionResponse = (
        state_machine._make_control_mission_response()
    )
    state_machine.events.api_requests.resume_mission.output.put(resume_mission_response)

    state_machine.robot.resume()
    return True
