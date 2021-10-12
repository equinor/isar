import time

from isar.models.mission import Mission
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.state_machine import StateMachine
from isar.storage.storage_interface import StorageInterface
from models.enums.mission_status import MissionStatus
from models.enums.states import States
from models.geometry.frame import Frame
from models.geometry.position import Position
from models.planning.step import DriveToPose, TakeImage
from robot_interfaces.robot_interface import RobotInterface
from tests.integration.state_machine.test_state_machine import (
    start_state_machine_in_thread,
)
from tests.mocks.blob_storage import BlobStorageMock
from tests.test_utilities.mock_interface.mock_robot_interface import MockRobot
from tests.test_utilities.mock_models.mock_robot_variables import mock_pose


def test_data_offload(injector, mocker):
    injector.binder.bind(RobotInterface, to=MockRobot())
    injector.binder.bind(StorageInterface, to=BlobStorageMock())

    state_machine: StateMachine = start_state_machine_in_thread(injector=injector)

    step_1: DriveToPose = DriveToPose(pose=mock_pose())
    step_2: TakeImage = TakeImage(target=Position(x=1, y=1, z=1, frame=Frame.Robot))
    step_3: TakeImage = TakeImage(target=Position(x=1, y=1, z=1, frame=Frame.Robot))
    step_4: DriveToPose = DriveToPose(pose=mock_pose())

    mission: Mission = Mission([step_1, step_2, step_3, step_4])

    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)

    message, _ = scheduling_utilities.start_mission(mission=mission)
    assert message.started

    time.sleep(1)
    assert state_machine.status.current_state is States.Monitor
    assert state_machine.status.current_mission_step == step_1

    mocker.patch.object(
        MockRobot,
        "mission_status",
        side_effect=[MissionStatus.Completed] + 10 * [MissionStatus.InProgress],
    )
    time.sleep(1)
    assert state_machine.status.current_state is States.Monitor
    assert state_machine.status.current_mission_step == step_2

    mocker.patch.object(
        MockRobot,
        "mission_status",
        side_effect=[MissionStatus.Completed] + 10 * [MissionStatus.InProgress],
    )

    time.sleep(1)
    assert state_machine.status.current_state is States.Monitor
    assert state_machine.status.current_mission_step == step_3
    assert len(state_machine.status.mission_schedule.inspections) == 1

    mocker.patch.object(
        MockRobot,
        "mission_status",
        side_effect=[MissionStatus.Completed] + 10 * [MissionStatus.InProgress],
    )
    time.sleep(1)
    assert state_machine.status.current_state is States.Monitor
    assert state_machine.status.current_mission_step == step_4
    assert len(state_machine.status.mission_schedule.inspections) == 2

    mocker.patch.object(
        MockRobot, "mission_status", side_effect=[MissionStatus.Completed]
    )
    time.sleep(1)

    assert state_machine.status.current_state is States.Idle
