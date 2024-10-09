from isar.apis.models.models import (
    InputOrientation,
    InputPose,
    InputPosition,
    StartMissionResponse,
    TaskResponse,
)
from isar.apis.models.start_mission_definition import (
    InspectionTypes,
    StartMissionDefinition,
    StartMissionInspectionDefinition,
    StartMissionTaskDefinition,
)
from robot_interface.models.mission.mission import Mission
from tests.mocks.task import MockTask


class MockMissionDefinition:
    mock_input_position = InputPosition(x=1, y=1, z=1, frame_name="robot")
    mock_input_orientation = InputOrientation(x=0, y=0, z=0, w=0, frame_name="robot")
    mock_input_pose = InputPose(
        position=mock_input_position,
        orientation=mock_input_orientation,
        frame_name="robot",
    )
    mock_input_target_position = InputPosition(x=5, y=5, z=5, frame_name="robot")
    mock_task_take_image = MockTask.take_image()
    mock_task_return_home = MockTask.return_home()
    default_mission = Mission(
        id="default_mission",
        tasks=[
            mock_task_take_image,
            mock_task_return_home,
        ],
    )
    mock_start_mission_inspection_definition = StartMissionInspectionDefinition(
        type=InspectionTypes.image,
        inspection_target=mock_input_target_position,
    )
    mock_start_mission_inspection_definition_id_123 = StartMissionInspectionDefinition(
        type=InspectionTypes.image,
        inspection_target=mock_input_target_position,
        id="123",
    )
    mock_start_mission_inspection_definition_id_123456 = (
        StartMissionInspectionDefinition(
            type=InspectionTypes.image,
            inspection_target=mock_input_target_position,
            id="123456",
        )
    )
    mock_task_response_take_image = TaskResponse(
        id=mock_task_take_image.id,
        tag_id=mock_task_take_image.tag_id,
        type=mock_task_take_image.type,
    )

    mock_task_response_return_home = TaskResponse(
        id=mock_task_return_home.id,
        tag_id=mock_task_return_home.tag_id,
        type=mock_task_return_home.type,
    )
    mock_start_mission_response = StartMissionResponse(
        id=default_mission.id,
        tasks=[mock_task_response_take_image, mock_task_response_return_home],
    )
    mock_start_mission_definition = StartMissionDefinition(
        tasks=[
            StartMissionTaskDefinition(
                pose=mock_input_pose,
                tag="dummy_tag",
                inspection=mock_start_mission_inspection_definition,
            ),
        ]
    )
    mock_start_mission_definition_task_ids = StartMissionDefinition(
        tasks=[
            StartMissionTaskDefinition(
                pose=mock_input_pose,
                tag="dummy_tag",
                inspection=mock_start_mission_inspection_definition_id_123,
                id="123",
            ),
            StartMissionTaskDefinition(
                pose=mock_input_pose,
                tag="dummy_tag",
                inspection=mock_start_mission_inspection_definition,
                id="123456",
            ),
            StartMissionTaskDefinition(
                pose=mock_input_pose,
                tag="dummy_tag",
                inspection=mock_start_mission_inspection_definition,
                id="123456789",
            ),
        ]
    )
    mock_start_mission_definition_with_duplicate_task_ids = StartMissionDefinition(
        tasks=[
            StartMissionTaskDefinition(
                pose=mock_input_pose,
                tag="dummy_tag",
                inspection=mock_start_mission_inspection_definition,
                id="123",
            ),
            StartMissionTaskDefinition(
                pose=mock_input_pose,
                tag="dummy_tag",
                inspection=mock_start_mission_inspection_definition,
                id="123456",
            ),
            StartMissionTaskDefinition(
                pose=mock_input_pose,
                tag="dummy_tag",
                inspection=mock_start_mission_inspection_definition,
                id="123",
            ),
        ]
    )
