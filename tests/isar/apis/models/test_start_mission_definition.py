from isar.apis.models.models import InputOrientation, InputPose, InputPosition
from isar.apis.models.start_mission_definition import (
    InspectionTypes,
    StartMissionDefinition,
    StartMissionInspectionDefinition,
    StartMissionTaskDefinition,
    TaskType,
    to_isar_mission,
)
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import TakeImage


def test_to_isar_mission():

    DUMMY_MISSION_ID = "123-45-567"
    DUMMY_MISSION_NAME = "mission_name"
    DUMMY_ISAR_TASK_ID = "abc-de-fgh"

    inspection_definition = StartMissionInspectionDefinition(
        type=InspectionTypes.image,
        inspection_target=InputPosition(x=0, y=0, z=0),
        id=DUMMY_ISAR_TASK_ID,
    )
    task_pose = InputPose(
        position=InputPosition(x=0, y=0, z=0),
        orientation=InputOrientation(x=0, y=0, z=0, w=0),
    )
    task_definition = StartMissionTaskDefinition(
        type=TaskType.Inspection, pose=task_pose, inspection=inspection_definition
    )
    mission_definition = StartMissionDefinition(
        tasks=[task_definition], id=DUMMY_MISSION_ID, name=DUMMY_MISSION_NAME
    )

    # expected_task = TakeImage()

    # # expected_mission = Mission(
    # #     tasks=[expected_task], id=DUMMY_MISSION_ID, name=DUMMY_MISSION_NAME
    # # )

    resulting_isar_mission = to_isar_mission(mission_definition)

    assert resulting_isar_mission.tasks[0].inspection.id == DUMMY_ISAR_TASK_ID
