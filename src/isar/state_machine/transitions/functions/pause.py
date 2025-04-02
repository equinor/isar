from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine

from isar.apis.models.models import ControlMissionResponse
from robot_interface.models.mission.status import MissionStatus, TaskStatus


def pause_mission(state_machine: "StateMachine") -> bool:
    state_machine.logger.info("Pausing mission: %s", state_machine.current_mission.id)
    state_machine.current_mission.status = MissionStatus.Paused
    state_machine.current_task.status = TaskStatus.Paused

    paused_mission_response: ControlMissionResponse = (
        state_machine._make_control_mission_response()
    )
    state_machine.events.api_requests.pause_mission.output.put(paused_mission_response)

    state_machine.publish_mission_status()
    state_machine.publish_task_status(task=state_machine.current_task)

    state_machine.robot.pause()
    return True
