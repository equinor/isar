from typing import Literal

from isar.models.communication.status import Status
from isar.models.mission import Mission
from models.enums.mission_status import MissionStatus
from models.enums.states import States
from models.planning.step import Step
from tests.test_utilities.mock_models.mock_mission_definition import (
    mock_mission_definition,
)
from tests.test_utilities.mock_models.mock_step import MockStep


def mock_status(
    mission_in_progress: bool = True,
    current_mission_instance_id: int = 1053,
    current_mission_step: Step = MockStep.take_image_in_coordinate_direction(),
    mission_status: MissionStatus = MissionStatus.Scheduled,
    current_state: States = States.Idle,
    mission_schedule: Mission = mock_mission_definition(),
) -> Status:
    scheduled_status = Status(
        mission_status=mission_status,
        mission_in_progress=mission_in_progress,
        current_mission_instance_id=current_mission_instance_id,
        current_mission_step=current_mission_step,
        mission_schedule=mission_schedule,
        current_state=current_state,
    )
    return scheduled_status
