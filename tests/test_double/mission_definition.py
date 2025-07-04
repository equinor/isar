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
from robot_interface.models.mission.status import MissionStatus, TaskStatus
from tests.test_double.task import StubTask


class DummyMissionDefinition:
    dummy_input_position = InputPosition(x=1, y=1, z=1, frame_name="robot")
    dummy_input_orientation = InputOrientation(x=0, y=0, z=0, w=0, frame_name="robot")
    dummy_input_pose = InputPose(
        position=dummy_input_position,
        orientation=dummy_input_orientation,
        frame_name="robot",
    )
    dummy_input_target_position = InputPosition(x=5, y=5, z=5, frame_name="robot")
    dummy_task_take_image = StubTask.take_image()
    default_mission = Mission(
        id="default_mission",
        name="Dummy misson",
        tasks=[
            dummy_task_take_image,
        ],
    )
    dummy_task_take_image_cancelled = StubTask.take_image(status=TaskStatus.Cancelled)
    stopped_mission = Mission(
        id="default_mission",
        name="Dummy misson",
        tasks=[
            dummy_task_take_image_cancelled,
        ],
        status=MissionStatus.Cancelled,
    )
    dummy_start_mission_inspection_definition = StartMissionInspectionDefinition(
        type=InspectionTypes.image,
        inspection_target=dummy_input_target_position,
    )
    dummy_task_response_take_image = TaskResponse(
        id=dummy_task_take_image.id,
        tag_id=dummy_task_take_image.tag_id,
        inspection_id=dummy_task_take_image.inspection_id,
        type=dummy_task_take_image.type,
    )

    dummy_start_mission_response = StartMissionResponse(
        id=default_mission.id,
        tasks=[dummy_task_response_take_image],
    )
    dummy_start_mission_definition = StartMissionDefinition(
        tasks=[
            StartMissionTaskDefinition(
                pose=dummy_input_pose,
                tag="dummy_tag",
                inspection=dummy_start_mission_inspection_definition,
            ),
        ]
    )
    dummy_start_mission_definition_task_ids = StartMissionDefinition(
        tasks=[
            StartMissionTaskDefinition(
                pose=dummy_input_pose,
                tag="dummy_tag",
                inspection=dummy_start_mission_inspection_definition,
            ),
            StartMissionTaskDefinition(
                pose=dummy_input_pose,
                tag="dummy_tag",
                inspection=dummy_start_mission_inspection_definition,
            ),
            StartMissionTaskDefinition(
                pose=dummy_input_pose,
                tag="dummy_tag",
                inspection=dummy_start_mission_inspection_definition,
            ),
        ]
    )
