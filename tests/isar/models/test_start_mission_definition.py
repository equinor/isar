import json
import os
from typing import List

import pytest
from alitra import Frame, Orientation, Pose, Position

from isar.apis.models.start_mission_definition import (
    StartMissionDefinition,
    get_duplicate_ids,
    to_isar_mission,
)
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import TASKS, Task

task_1: Task = Task(tag_id=None, id="123")
task_2: Task = Task(tag_id=None, id="123")
task_3: Task = Task(tag_id=None, id="123456")
task_4: Task = Task()
task_5: Task = Task()


@pytest.mark.parametrize(
    "item_list, expected_boolean",
    [
        (
            [task_1, task_2, task_3],
            True,
        ),
        (
            [task_1, task_3, task_4, task_5],
            False,
        ),
    ],
)
def test_duplicate_id_check(item_list: List[TASKS], expected_boolean: bool):
    duplicates: List[str] = get_duplicate_ids(item_list)
    has_duplicates: bool = len(duplicates) > 0
    assert has_duplicates == expected_boolean


def test_mission_definition_to_isar_mission():
    dirname = os.path.dirname(__file__)
    filepath = os.path.join(dirname, "example_mission_definition.json")

    with open(filepath) as f:
        datax = json.load(f)
        mission_definition = StartMissionDefinition(**datax)

    generated_mission: Mission = to_isar_mission(mission_definition)
    assert generated_mission.id == "generated_mission_id"
    assert generated_mission.name == "my-mission"
    assert len(generated_mission.tasks) == 1

    task = generated_mission.tasks[0]
    assert task.id == "generated_task_id"
    assert task.robot_pose == Pose(
        position=Position(0.0, 0.0, 0.0, frame=Frame("robot")),
        orientation=Orientation(0.0, 0.0, 0.0, 0.0, frame=Frame("robot")),
        frame=Frame("robot"),
    )
    assert task.type == "take_image"
    assert task.target == Position(0.0, 0.0, 0.0, frame=Frame("robot"))
