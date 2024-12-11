from typing import Iterator, List

from isar.mission_planner.task_selector_interface import (
    TaskSelectorInterface,
    TaskSelectorStop,
)
from robot_interface.models.mission.task import TASKS


class SequentialTaskSelector(TaskSelectorInterface):
    def __init__(self) -> None:
        super().__init__()
        self._iterator: Iterator = None

    def initialize(self, tasks: List[TASKS]) -> None:
        super().initialize(tasks=tasks)
        self._iterator = iter(self.tasks)

    def next_task(self) -> TASKS:
        try:
            return next(self._iterator)
        except StopIteration:
            raise TaskSelectorStop
