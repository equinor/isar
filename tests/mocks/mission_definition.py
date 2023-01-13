from isar.apis.models.models import (
    InputOrientation,
    InputPose,
    InputPosition,
    StartMissionResponse,
    StepResponse,
    TaskResponse,
)
from isar.apis.models.start_mission_definition import (
    StartMissionDefinition,
    StartMissionTaskDefinition,
)
from isar.models.mission import Mission, Task
from tests.mocks.step import MockStep


class MockMissionDefinition:
    mock_input_position = InputPosition(x=1, y=1, z=1, frame_name="robot")
    mock_input_orientation = InputOrientation(x=0, y=0, z=0, w=0, frame_name="robot")
    mock_input_pose = InputPose(
        position=mock_input_position,
        orientation=mock_input_orientation,
        frame_name="robot",
    )
    mock_input_target_position = InputPosition(x=5, y=5, z=5, frame_name="robot")
    default_mission = Mission(
        id="default_mission",
        tasks=[
            Task(
                steps=[MockStep.take_image_in_coordinate_direction, MockStep.drive_to]
            ),
            Task(
                steps=[
                    MockStep.take_image_in_coordinate_direction,
                    MockStep.take_image_in_coordinate_direction,
                ]
            ),
        ],
    )
    mock_start_mission_response = StartMissionResponse(
        id=default_mission.id,
        tasks=[
            TaskResponse(
                id=task.id,
                tag_id=task.tag_id,
                steps=[
                    StepResponse(id=step.id, type=step.__class__.__name__)
                    for step in task.steps
                ],
            )
            for task in default_mission.tasks
        ],
    )
    mock_start_mission_definition = StartMissionDefinition(
        tasks=[
            StartMissionTaskDefinition(
                pose=mock_input_pose,
                tag="dummy_tag",
                inspection_target=mock_input_target_position,
                inspection_types=["Image"],
                video_duration=None,
            ),
        ]
    )
