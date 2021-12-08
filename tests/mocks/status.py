from isar.models.communication.status import Status
from isar.models.mission import Mission
from isar.state_machine.states_enum import States
from robot_interface.models.mission import Task, TaskStatus
from tests.mocks.mission_definition import mock_mission_definition
from tests.mocks.task import MockTask


def mock_status(
    mission_in_progress: bool = True,
    task_status: TaskStatus = TaskStatus.Scheduled,
    current_task: Task = MockTask.take_image_in_coordinate_direction(),
    current_state: States = States.Idle,
    current_mission: Mission = mock_mission_definition(),
) -> Status:

    current_task.status = task_status
    scheduled_status = Status(
        mission_in_progress=mission_in_progress,
        current_task=current_task,
        current_state=current_state,
        current_mission=current_mission,
    )
    return scheduled_status
