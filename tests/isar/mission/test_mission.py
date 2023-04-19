from alitra import Frame, Orientation, Pose, Position

from isar.services.readers.base_reader import BaseReader
from robot_interface.models.mission.mission import Mission, Task
from robot_interface.models.mission.step import (
    DriveToPose,
    STEPS,
    TakeImage,
    TakeThermalImage,
)

drive_to_pose_1 = DriveToPose(
    pose=Pose(
        position=Position(x=2, y=2, z=0, frame=Frame(name="asset")),
        orientation=Orientation(
            x=0, y=0, z=0.7071068, w=0.7071068, frame=Frame(name="asset")
        ),
        frame=Frame(name="asset"),
    ),
)

take_image_1 = TakeImage(target=Position(x=2, y=3, z=1, frame=Frame(name="asset")))

drive_to_pose_2 = DriveToPose(
    pose=Pose(
        position=Position(x=4, y=4, z=0, frame=Frame(name="asset")),
        orientation=Orientation(
            x=0, y=0, z=-0.7071068, w=0.7071068, frame=Frame(name="asset")
        ),
        frame=Frame(name="asset"),
    ),
)

take_image_2 = TakeThermalImage(
    target=Position(x=4, y=3, z=1, frame=Frame(name="asset"))
)

drive_to_pose_3 = DriveToPose(
    pose=Pose(
        position=Position(x=0, y=0, z=0, frame=Frame(name="asset")),
        orientation=Orientation(x=0, y=0, z=0, w=1, frame=Frame(name="asset")),
        frame=Frame(name="asset"),
    ),
)

expected_mission = Mission(
    id="1",
    tasks=[
        Task(id="11", steps=[drive_to_pose_1, take_image_1]),
        Task(id="12", steps=[drive_to_pose_2, take_image_2]),
        Task(id="13", steps=[drive_to_pose_3]),
    ],
)


example_mission_dict = {
    "id": "1",
    "tasks": [
        {
            "steps": [
                {
                    "type": "drive_to_pose",
                    "pose": {
                        "position": {
                            "x": 2,
                            "y": 2,
                            "z": 0,
                            "frame": {"name": "asset"},
                        },
                        "orientation": {
                            "x": 0,
                            "y": 0,
                            "z": 0.7071068,
                            "w": 0.7071068,
                            "frame": {"name": "asset"},
                        },
                        "frame": {"name": "asset"},
                    },
                },
                {
                    "type": "take_image",
                    "target": {"x": 2, "y": 3, "z": 1, "frame": {"name": "asset"}},
                },
            ],
        },
        {
            "steps": [
                {
                    "type": "drive_to_pose",
                    "pose": {
                        "position": {
                            "x": 4,
                            "y": 4,
                            "z": 0,
                            "frame": {"name": "asset"},
                        },
                        "orientation": {
                            "x": 0,
                            "y": 0,
                            "z": -0.7071068,
                            "w": 0.7071068,
                            "frame": {"name": "asset"},
                        },
                        "frame": {"name": "asset"},
                    },
                },
                {
                    "type": "take_thermal_image",
                    "target": {"x": 4, "y": 3, "z": 1, "frame": {"name": "asset"}},
                },
            ],
        },
        {
            "steps": [
                {
                    "type": "drive_to_pose",
                    "pose": {
                        "position": {
                            "x": 0,
                            "y": 0,
                            "z": 0,
                            "frame": {"name": "asset"},
                        },
                        "orientation": {
                            "x": 0,
                            "y": 0,
                            "z": 0,
                            "w": 1,
                            "frame": {"name": "asset"},
                        },
                        "frame": {"name": "asset"},
                    },
                }
            ],
        },
    ],
}


def test_mission_definition() -> None:
    loaded_mission: Mission = BaseReader.dict_to_dataclass(
        dataclass_dict=example_mission_dict,
        target_dataclass=Mission,
        strict_config=True,
    )

    assert loaded_mission.id == expected_mission.id
    assert loaded_mission.status == expected_mission.status

    assert len(loaded_mission.tasks) == len(expected_mission.tasks)
    for i_task in range(len(loaded_mission.tasks)):
        loaded_task: Task = loaded_mission.tasks[i_task]
        expected_task: Task = expected_mission.tasks[i_task]

        assert loaded_task.status == expected_task.status
        assert loaded_task.tag_id == expected_task.tag_id

        for i_step in range(len(loaded_task.steps)):
            loaded_step: STEPS = loaded_task.steps[i_step]
            expected_step: STEPS = expected_task.steps[i_step]

            ignore_attributes = set(
                ("id", "status", "tag_id", "error_message", "analysis")
            )
            loaded_attributes = set(loaded_step.__dict__.keys()) - ignore_attributes
            expected_attributes = set(expected_step.__dict__.keys()) - ignore_attributes

            assert loaded_attributes == expected_attributes

            for attr in loaded_attributes:
                assert loaded_step.__dict__[attr] == expected_step.__dict__[attr]
