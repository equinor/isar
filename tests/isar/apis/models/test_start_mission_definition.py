import json
import os

from alitra import Frame, Orientation, Pose, Position

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


def test_to_isar_mission() -> None:
    DUMMY_MISSION_NAME = "mission_name"

    inspection_definition = StartMissionInspectionDefinition(
        type=InspectionTypes.image,
        inspection_target=InputPosition(x=1, y=1, z=1),
    )
    task_pose = InputPose(
        position=InputPosition(x=1, y=1, z=1),
        orientation=InputOrientation(x=1, y=1, z=1, w=1),
    )
    task_definition = StartMissionTaskDefinition(
        type=TaskType.Inspection,
        pose=task_pose,
        inspection=inspection_definition,
    )
    mission_definition = StartMissionDefinition(
        tasks=[task_definition], name=DUMMY_MISSION_NAME
    )

    isar_mission: Mission = to_isar_mission(mission_definition)

    assert len(isar_mission.id) > 1
    assert isar_mission.name == DUMMY_MISSION_NAME
    assert len(isar_mission.tasks) == 1

    first_task = isar_mission.tasks[0]
    assert len(first_task.id) > 1

    assert isinstance(first_task, TakeImage)

    assert first_task.target == Position(x=1, y=1, z=1, frame=Frame(name="robot"))
    assert len(first_task.inspection_id) > 1
    assert first_task.robot_pose == Pose(
        position=Position(x=1, y=1, z=1, frame=Frame(name="robot")),
        orientation=Orientation(x=1, y=1, z=1, w=1, frame=Frame(name="robot")),
        frame=Frame(name="robot"),
    )


def test_mission_definition_from_json_to_isar_mission() -> None:
    dirname = os.path.dirname(__file__)
    filepath = os.path.join(dirname, "example_mission_definition.json")

    with open(filepath) as f:
        datax = json.load(f)
        mission_definition = StartMissionDefinition(**datax)

    isar_mission: Mission = to_isar_mission(mission_definition)
    assert len(isar_mission.id) > 1
    assert isar_mission.name == "my-mission"

    assert len(isar_mission.tasks) == 1
    task = isar_mission.tasks[0]
    assert len(task.id) > 1
    assert isinstance(task, TakeImage)
    assert task.robot_pose == Pose(
        position=Position(0.0, 0.0, 0.0, frame=Frame("robot")),
        orientation=Orientation(0.0, 0.0, 0.0, 0.0, frame=Frame("robot")),
        frame=Frame("robot"),
    )
    assert task.type == "take_image"
    assert task.target == Position(0.0, 0.0, 0.0, frame=Frame("robot"))
