import json
import os
from typing import List, Union

import pytest
from alitra import Frame, Orientation, Pose, Position

from isar.apis.models.start_mission_definition import (
    StartMissionDefinition,
    get_duplicate_ids,
    to_isar_mission,
)
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.step import STEPS, Step
from robot_interface.models.mission.task import Task

task_1: Task = Task([], tag_id=None, id="123")
task_2: Task = Task([], tag_id=None, id="123")
task_3: Task = Task([], tag_id=None, id="123456")
task_4: Task = Task([])
task_5: Task = Task([])

step_1: Step = Step()
step_1.id = "123"
step_2: Step = Step()
step_2.id = "123"
step_3: Step = Step()
step_3.id = "123456"


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
        (
            [step_1, step_2, step_3],
            True,
        ),
        (
            [step_1, step_3],
            False,
        ),
        (
            [step_1, step_3],
            False,
        ),
    ],
)
def test_duplicate_id_check(
    item_list: Union[List[Task], List[STEPS]], expected_boolean: bool
):
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
    assert task.tag_id == "MY-TAG-123"

    first_step = task.steps[0]
    # assert first_step.id == "generated_inspection_id"
    assert first_step.type == "drive_to_pose"
    assert first_step.pose == Pose(
        position=Position(0.0, 0.0, 0.0, frame=Frame("robot")),
        orientation=Orientation(0.0, 0.0, 0.0, 0.0, frame=Frame("robot")),
        frame=Frame("robot"),
    )

    second_step = task.steps[1]
    # assert second_step.id == "generated_inspection_id"
    assert second_step.type == "take_image"
    assert second_step.tag_id == "MY-TAG-123"
    assert second_step.target == Position(0.0, 0.0, 0.0, frame=Frame("robot"))
