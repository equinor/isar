from alitra import Frame, Orientation, Pose, Position

from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import (
    TASKS,
    ReturnToHome,
    TakeImage,
    TakeThermalImage,
)

robot_pose_1 = Pose(
    position=Position(x=2, y=2, z=0, frame=Frame(name="asset")),
    orientation=Orientation(
        x=0, y=0, z=0.7071068, w=0.7071068, frame=Frame(name="asset")
    ),
    frame=Frame(name="asset"),
)

robot_pose_2 = Pose(
    position=Position(x=4, y=4, z=0, frame=Frame(name="asset")),
    orientation=Orientation(
        x=0, y=0, z=-0.7071068, w=0.7071068, frame=Frame(name="asset")
    ),
    frame=Frame(name="asset"),
)


task_take_image = TakeImage(
    target=Position(x=2, y=3, z=1, frame=Frame(name="asset")),
    robot_pose=robot_pose_1,
)

task_take_thermal_image = TakeThermalImage(
    target=Position(x=4, y=3, z=1, frame=Frame(name="asset")),
    robot_pose=robot_pose_2,
)

task_return_to_home = ReturnToHome()

expected_mission = Mission(
    id="1",
    name="Test mission",
    tasks=[task_take_image, task_take_thermal_image, task_return_to_home],
)

example_mission_dict = {
    "id": "1",
    "name": "Test mission",
    "tasks": [
        {
            "type": "take_image",
            "target": {"x": 2, "y": 3, "z": 1, "frame": {"name": "asset"}},
            "robot_pose": {
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
            "type": "take_thermal_image",
            "target": {"x": 4, "y": 3, "z": 1, "frame": {"name": "asset"}},
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
            "type": "return_to_home",
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
        },
    ],
}


def test_mission_definition() -> None:
    loaded_mission: Mission = Mission(**example_mission_dict)

    assert loaded_mission.id == expected_mission.id
    assert loaded_mission.id == expected_mission.id
    assert loaded_mission.status == expected_mission.status

    assert len(loaded_mission.tasks) == len(expected_mission.tasks)
    for i_task in range(len(loaded_mission.tasks)):
        loaded_task: TASKS = loaded_mission.tasks[i_task]
        expected_task: TASKS = expected_mission.tasks[i_task]

        assert loaded_task.status == expected_task.status
        assert loaded_task.tag_id == expected_task.tag_id
