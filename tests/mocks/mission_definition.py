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
    default_mission = Mission(
        id="default_mission",
        name="Dummy misson",
        tasks=[
            mock_task_take_image,
        ],
    )
    mock_start_mission_inspection_definition = StartMissionInspectionDefinition(
        type=InspectionTypes.image,
        inspection_target=mock_input_target_position,
    )
    mock_task_response_take_image = TaskResponse(
        id=mock_task_take_image.id,
        tag_id=mock_task_take_image.tag_id,
        inspection_id=mock_task_take_image.inspection_id,
        type=mock_task_take_image.type,
    )

    mock_start_mission_response = StartMissionResponse(
        id=default_mission.id,
        tasks=[mock_task_response_take_image],
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
                inspection=mock_start_mission_inspection_definition,
            ),
            StartMissionTaskDefinition(
                pose=mock_input_pose,
                tag="dummy_tag",
                inspection=mock_start_mission_inspection_definition,
            ),
            StartMissionTaskDefinition(
                pose=mock_input_pose,
                tag="dummy_tag",
                inspection=mock_start_mission_inspection_definition,
            ),
        ]
    )
