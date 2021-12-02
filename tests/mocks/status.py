from isar.models.communication.status import Status
from isar.models.mission import Mission
from isar.state_machine.states_enum import States
from robot_interface.models.mission import MissionStatus, Task
from tests.mocks.mission_definition import mock_mission_definition
from tests.mocks.task import MockTask


def mock_status(
    mission_in_progress: bool = True,
    current_task: Task = MockTask.take_image_in_coordinate_direction(),
    mission_status: MissionStatus = MissionStatus.Scheduled,
    current_state: States = States.Idle,
    mission_schedule: Mission = mock_mission_definition(),
) -> Status:
    scheduled_status = Status(
        mission_status=mission_status,
        mission_in_progress=mission_in_progress,
        current_task=current_task,
        mission_schedule=mission_schedule,
        current_state=current_state,
    )
    return scheduled_status
