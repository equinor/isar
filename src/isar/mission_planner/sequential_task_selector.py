from typing import Iterator, List

from isar.mission_planner.task_selector_interface import (
    TaskSelectorInterface,
    TaskSelectorStop,
)
from isar.models.mission import Task


class SequentialTaskSelector(TaskSelectorInterface):
    def __init__(self) -> None:
        super().__init__()
        self._iterator: Iterator = None

    def initialize(self, tasks: List[Task]) -> None:
        super().initialize(tasks=tasks)
        self._iterator = iter(self.tasks)

    def next_task(self) -> Task:
        try:
            return next(self._iterator)
        except StopIteration:
            raise TaskSelectorStop
