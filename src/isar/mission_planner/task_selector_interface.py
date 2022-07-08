from abc import ABCMeta, abstractmethod
from typing import List

from isar.models.mission import Task


class TaskSelectorInterface(metaclass=ABCMeta):
    def __init__(self) -> None:
        self.tasks: List[Task] = None

    def initialize(self, tasks: List[Task]) -> None:
        self.tasks = tasks

    @abstractmethod
    def next_task(self) -> Task:
        """
        Returns
        -------
        Task
            Returns the next task from the list of tasks

        Raises
        ------
        TaskSelectorStop
            If all tasks have been selected, and the task selection process is complete.
        """
        pass


class TaskSelectorStop(Exception):
    pass
