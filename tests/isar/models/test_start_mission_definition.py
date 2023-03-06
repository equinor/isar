from typing import List, Union

import pytest

from isar.apis.models.start_mission_definition import get_duplicate_ids
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
