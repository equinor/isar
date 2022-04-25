from isar.models.communication.status import Status
from isar.models.mission import Mission
from isar.state_machine.states_enum import States
from robot_interface.models.mission import Step, StepStatus
from tests.mocks.mission_definition import MockMissionDefinition
from tests.mocks.step import MockStep


def mock_status(
    mission_in_progress: bool = True,
    step_status: StepStatus = StepStatus.Scheduled,
    current_step: Step = MockStep.take_image_in_coordinate_direction,
    current_state: States = States.Idle,
    current_mission: Mission = MockMissionDefinition.default_mission,
) -> Status:

    current_step.status = step_status
    scheduled_status = Status(
        mission_in_progress=mission_in_progress,
        current_step=current_step,
        current_state=current_state,
        current_mission=current_mission,
    )
    return scheduled_status
