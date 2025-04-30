from typing import TYPE_CHECKING

from isar.models.communication.queues.queue_utils import trigger_event_without_data

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine

from isar.apis.models.models import ControlMissionResponse
from robot_interface.models.mission.status import MissionStatus, TaskStatus


def trigger_stop_mission_event(state_machine: "StateMachine") -> bool:
    trigger_event_without_data(state_machine.events.state_machine_events.stop_mission)
    return True


def stop_mission_cleanup(state_machine: "StateMachine") -> bool:
    if state_machine.current_mission is None:
        state_machine._queue_empty_response()
        state_machine.reset_state_machine()
        return True

    state_machine.current_mission.status = MissionStatus.Cancelled

    for task in state_machine.current_mission.tasks:
        if task.status in [
            TaskStatus.NotStarted,
            TaskStatus.InProgress,
            TaskStatus.Paused,
        ]:
            task.status = TaskStatus.Cancelled

    stopped_mission_response: ControlMissionResponse = (
        state_machine._make_control_mission_response()
    )
    state_machine.events.api_requests.stop_mission.output.put(stopped_mission_response)
    state_machine.publish_task_status(task=state_machine.current_task)
    state_machine._finalize()
    return True


def stop_return_home_mission_cleanup(state_machine: "StateMachine") -> bool:
    if state_machine.current_mission is None:
        state_machine._queue_empty_response()
        state_machine.reset_state_machine()
        return True

    state_machine._finalize()
    return True
